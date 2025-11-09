import cmd
from sqlalchemy import select, text
from tractatus_orm.database import SessionLocal, init_db
from tractatus_orm.models import Proposition, Translation


class TractatusCLI(cmd.Cmd):
    intro = "Tractatus ORM CLI. Type help or ? to list commands.\n"
    prompt = "(tractatus) "

    def __init__(self):
        super().__init__()
        init_db()
        self.session = SessionLocal()
        self.current: Proposition | None = None
    
    def default(self, line: str):
        """Fallback for unknown input — interpret bare numbers as 'get <name>'."""
        text = line.strip()
        if not text:
            return  # ignore empty lines
        
        # If user typed something like 1, 1.1, 5.2, etc.
        if text[0].isdigit() or text.startswith("id:") or text.startswith("name:"):
            # Redirect to the get command
            return self.do_get(text)
        
        # Otherwise, unknown command
        print(f"Unknown syntax: {line}")
        

    def do_get(self, arg):
        """get <value> — jump by name (default) or id:<n> if explicit"""
        key = arg.strip()
        if not key:
            print("Usage: get <name> or get id:<n>")
            return
        
        # --- explicit id override ---
        if key.startswith("id:"):
            try:
                value = int(key.removeprefix("id:"))
            except ValueError:
                print("Invalid id syntax. Use: get id:<integer>")
                return
            chosen = self.session.get(Proposition, value)
            if not chosen:
                print(f"No record found for id {value}")
                return
            self.current = chosen
            print(f"(id) {chosen.name}: {chosen.text}")
            return
        
        # --- default: name-first resolution ---
        name_hit = self.session.scalars(
            select(Proposition).where(Proposition.name == key)
        ).first()
        
        if name_hit:
            self.current = name_hit
            print(f"{name_hit.name}: {name_hit.text}")
            return
        
        # fallback: id lookup only if name not found
        if key.isdigit():
            id_hit = self.session.get(Proposition, int(key))
            if id_hit:
                print(f"(fallback by id) {id_hit.name}: {id_hit.text}")
                self.current = id_hit
                return
            
        print(f"No proposition found for '{key}'.")
        

    def do_parent(self, arg):
        """Show parent of current node"""
        if not self.current or not self.current.parent_id:
            print("No parent.")
            return
        parent = self.session.get(Proposition, self.current.parent_id)
        print(parent)
        self.current = parent

    def do_children(self, arg):
        """List children"""
        if not self.current:
            print("No current node.")
            return
        for child in self.current.children:
            print(f"{child.id:>4}  {child.name}: {child.text[:60]}")

    def do_tree(self, arg):
        """Recursively print subtree"""
        if not self.current:
            print("No current node.")
            return

        def print_tree(node, depth=0):
            print("  " * depth + f"{node.name}: {node.text}")
            for ch in node.children:
                print_tree(ch, depth + 1)

        print_tree(self.current)

    # --- translations ---
    def do_translations(self, arg):
        """List translations of current node"""
        if not self.current:
            print("No current node.")
            return
        for t in self.current.translations:
            print(f"[{t.lang}] {t.text[:60]} ({t.source or 'unknown'})")

    def do_translate(self, arg):
        """translate <lang> — show translation text"""
        if not self.current:
            print("No current node.")
            return
        lang = arg.strip()
        if not lang:
            print("Usage: translate <lang>")
            return
        stmt = select(Translation).where(
            Translation.tractatus_id == self.current.id,
            Translation.lang == lang
        )
        t = self.session.scalars(stmt).first()
        if t:
            print(t.text)
        else:
            print("No translation found.")

    # --- utility commands ---
    def do_search(self, arg):
        """search <term> — find propositions containing term"""
        term = f"%{arg.strip()}%"
        stmt = select(Proposition).where(Proposition.text.ilike(term))
        for p in self.session.scalars(stmt):
            print(f"{p.name}: {p.text[:60]}")

    def do_sql(self, arg):
        """sql <query> — execute raw SQL"""
        for row in self.session.execute(text(arg)):
            print(row)

    def do_exit(self, arg):
        """Exit"""
        print("Goodbye.")
        self.session.close()
        return True


if __name__ == "__main__":
    TractatusCLI().cmdloop()

    