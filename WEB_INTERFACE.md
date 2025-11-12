# Tractatus Web Interface

A Flask-based web wrapper for the Tractatus CLI, providing an interactive REST API and beautiful web UI for exploring Wittgenstein's *Tractatus Logico-Philosophicus*.

## Architecture

### Service Layer (`tractatus_service.py`)
- **TractatusService**: Encapsulates all CLI logic as reusable methods
- Returns JSON-serializable dictionaries (no print statements)
- Manages database session and application state
- Used by both CLI and Flask web app

### REST API (`web_app.py`)
- Flask application with CORS support
- HTTP endpoints for all Tractatus operations
- JSON request/response format
- Proper error handling

### Web UI (`static/`)
- Single-page application (SPA)
- HTML5 + CSS3 + Vanilla JavaScript
- No external dependencies (except Flask backend)
- Responsive design for desktop and mobile

## Installation

### 1. Install Dependencies
```bash
pip install flask flask-cors
# Plus existing Tractatus dependencies (sqlalchemy, etc.)
```

### 2. Run Web Server
```bash
python web_app.py
```

The web interface will be available at: **http://localhost:5000**

## API Routes

### Navigation
- `POST /api/current` - Get current proposition
- `POST /api/get` - Navigate to proposition by name or id
- `POST /api/parent` - Go to parent proposition
- `POST /api/next` - Go to next proposition
- `POST /api/previous` - Go to previous proposition

### Browsing
- `POST /api/list` - List children (optional: target)
- `POST /api/children` - List children of current
- `POST /api/tree` - Get tree view (optional: target)
- `POST /api/search` - Search propositions (term)

### Translations
- `POST /api/translations` - Get all translations
- `POST /api/translate` - Get specific translation (lang)

### LLM Analysis
- `POST /api/agent` - Invoke agent (action, targets)
  - Actions: `comment`, `comparison`, `websearch`, `reference`

### Configuration
- `GET /api/config` - Get all preferences
- `POST /api/config/set` - Set preference (key, value)

### Documentation
- `GET /api/help` - API documentation

## Usage Examples

### Via Web UI
1. Open http://localhost:5000
2. Click "Home" button to load Proposition 1
3. Use "List" to see children
4. Click on propositions to navigate
5. Use search to find propositions by text
6. Use "AI Analysis" tab for LLM commentary

### Via Command Input
```
get 1              # Navigate to proposition 1
list               # List children of current
next               # Go to next proposition
search world       # Search for propositions containing "world"
ag comment         # Get LLM commentary on current
```

### Via REST API
```bash
# Get a proposition
curl -X POST http://localhost:5000/api/get \
  -H "Content-Type: application/json" \
  -d '{"key": "1.1"}'

# Search
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"term": "world"}'

# Get AI commentary
curl -X POST http://localhost:5000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"action": "comment", "targets": ["1.1"]}'
```

## Web UI Features

### Tabs
1. **Children** - Browse direct children of current proposition
2. **Tree** - Hierarchical view with indentation
3. **Search** - Full-text search across propositions
4. **AI Analysis** - LLM-powered commentary and analysis
5. **Settings** - Configure preferences (display_length, llm_max_tokens, etc.)

### Quick Buttons
- **Home** - Jump to Proposition 1
- **List** - Show children
- **Next** - Go to next proposition
- **Prev** - Go to previous proposition
- **Parent** - Go to parent proposition

### Command History
- Automatically tracks command history
- Click history items to re-run commands
- Supports keyboard shortcuts (Enter to execute)

## Configuration

Preferences are stored in `~/.trclirc` and can be modified:

```json
{
  "display_length": 60,
  "lines_per_output": 10,
  "lang": "en",
  "llm_max_tokens": 500
}
```

Edit via:
- Web UI: Settings tab
- REST API: POST `/api/config/set`
- CLI: `set <key> <value>` command

## Command Format

The service supports natural command parsing:

```
get 1              # By name
get id:5           # By ID
list               # Current node
list 1.1           # Specific node
search term        # Full-text search
translate en       # Specific translation
ag comment         # LLM on current
ag comparison 1 2  # LLM comparing multiple
```

## Response Format

All API responses follow this format:

**Success:**
```json
{
  "success": true,
  "data": {
    // Response data varies by endpoint
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error message"
}
```

## Integration with CLI

The service layer enables both CLI and web to share:
- Same database operations
- Same LLM agent configuration
- Same preference system
- Same command parsing logic

To use service in CLI:
```python
from tractatus_service import TractatusService
from tractatus_orm.database import SessionLocal

session = SessionLocal()
service = TractatusService(session)
result = service.get('1.1')
```

## Development

### Adding New Endpoints
1. Add method to `TractatusService`
2. Create route in `web_app.py`
3. Add UI component in `static/app.js`

### Customizing Styles
Edit `static/style.css` for:
- Color scheme
- Layout
- Responsive breakpoints

### Extending Functionality
The modular design allows:
- Custom LLM actions
- Additional data visualization
- Alternative frontends (React, Vue, etc.)
- GraphQL API layer

## Performance Notes

- Single service instance shared across requests
- Database session per request for thread safety
- In-memory command history (last 20 commands)
- Lazy-load agent router on first use

## Future Enhancements

- User sessions and multi-user support
- Annotation/note system
- Export to PDF/Markdown
- Collaborative editing
- Mobile app
- WebSocket for real-time updates
- Full-text search indexing (SQLite FTS)
- Graph visualization of proposition relationships

## Troubleshooting

**No propositions loading:**
- Check database is initialized: `python -c "from tractatus_orm.database import init_db; init_db()"`
- Verify data file exists and is readable

**LLM not responding:**
- Set `OPENAI_API_KEY` environment variable
- Check `llm_max_tokens` setting (10-4000)
- Verify OpenAI account has credits

**Port already in use:**
- Change port in `web_app.py`: `app.run(port=5001)`
- Or kill existing process: `lsof -ti:5000 | xargs kill -9`

## License

Same as Tractatus project.
