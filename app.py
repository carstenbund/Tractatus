"""Flask web application for navigating Wittgenstein's Tractatus Logico-Philosophicus.

This module provides a RESTful API and web interface for exploring the hierarchical
structure of the Tractatus, with features including:
- Hierarchical navigation (parent, children, next, previous)
- Full-text search across all propositions
- Multilingual translations and alternative text versions
- AI-powered analysis using LLM agents
- User configuration management

The application wraps the core TractatusService in HTTP endpoints and serves
a single-page application from the static/ folder.
"""
from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import os
from tractatus_config import TrcliConfig
from tractatus_orm.database import SessionLocal, init_db
from tractatus_service import TractatusService

# Initialize Flask app with static file serving configuration
app = Flask(__name__, static_folder="static", static_url_path="/static")
# Enable Cross-Origin Resource Sharing for web client access
CORS(app)

# Initialize database connection and create tables if needed
init_db()

# Global service instance cache (maps session IDs to service instances)
# In production, this should use per-user sessions with proper session management
_service_cache: dict[str, TractatusService] = {}


def get_service() -> TractatusService:
    """Get or create a shared TractatusService instance.

    Returns a singleton service instance that maintains navigation state
    across requests. For multi-user production environments, this should
    be replaced with per-session instances using Flask session management.

    Returns:
        TractatusService: Shared service instance with database session and config
    """
    # For simplicity, use a single shared service instance
    # TODO: In production, implement per-user sessions with proper cleanup
    if "default" not in _service_cache:
        # Create new database session for ORM queries
        session = SessionLocal()
        # Load user configuration from ~/.trclirc
        config = TrcliConfig()
        # Initialize service with session and config
        _service_cache["default"] = TractatusService(session, config)
    service = _service_cache["default"]
    service.sync_preferences()
    return service


# --- Web UI Routes ---


@app.route("/")
def index():
    """Serve main web interface."""
    return send_from_directory("static", "index.html")


@app.route("/static/<path:path>")
def serve_static(path):
    """Serve static files."""
    return send_from_directory("static", path)


# --- API Routes ---


@app.route("/api/current", methods=["GET"])
def api_current():
    """Get current proposition."""
    service = get_service()
    if service.current:
        return jsonify({"success": True, "data": service._proposition_to_dict(service.current)})
    return jsonify({"success": False, "error": "No current proposition"})


@app.route("/api/get", methods=["POST"])
def api_get():
    """Navigate to a specific proposition by name or database ID.

    Accepts proposition names like "1", "1.1", "2.0121" or database IDs like "id:42".
    Sets this proposition as the current context for subsequent operations.

    Request JSON:
        key (str): Proposition name (e.g., "1.1") or database ID (e.g., "id:42")

    Returns:
        JSON response with proposition data or error message
    """
    data = request.get_json() or {}
    key = data.get("key", "").strip()

    # Validate that a key was provided
    if not key:
        return jsonify({"success": False, "error": "Key required"})

    service = get_service()
    # Retrieve the proposition and set it as current
    result = service.get(key)

    # Return error if proposition not found
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/parent", methods=["POST"])
def api_parent():
    """Navigate to parent."""
    service = get_service()
    result = service.parent()

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/next", methods=["POST"])
def api_next():
    """Navigate to next proposition."""
    service = get_service()
    result = service.next()

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/previous", methods=["POST"])
def api_previous():
    """Navigate to previous proposition."""
    service = get_service()
    result = service.previous()

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/children", methods=["POST"])
def api_children():
    """Get children of current node."""
    service = get_service()
    result = service.children()

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/list", methods=["POST"])
def api_list():
    """List children for target or current node."""
    data = request.get_json() or {}
    target = data.get("target", "").strip()

    service = get_service()
    result = service.list(target or None)

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/tree", methods=["POST"])
def api_tree():
    """Get tree for target or current node."""
    data = request.get_json() or {}
    target = data.get("target", "").strip()

    service = get_service()
    result = service.tree(target or None)

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/search", methods=["POST"])
def api_search():
    """Search propositions."""
    data = request.get_json() or {}
    term = data.get("term", "").strip()

    if not term:
        return jsonify({"success": False, "error": "Search term required"})

    service = get_service()
    result = service.search(term)

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/translations", methods=["POST"])
def api_translations():
    """Get translations of current node."""
    service = get_service()
    result = service.translations()

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/translate", methods=["POST"])
def api_translate():
    """Get specific translation."""
    data = request.get_json() or {}
    lang = data.get("lang", "").strip()

    if not lang:
        return jsonify({"success": False, "error": "Language code required"})

    service = get_service()
    result = service.translate(lang)

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/alternatives", methods=["GET"])
def api_alternatives_list():
    """Return alternative text variants for the active proposition."""

    service = get_service()
    result = service.alternatives()

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/alternatives", methods=["POST"])
def api_alternatives_create():
    """Create a new alternative text variant for the active proposition."""

    data = request.get_json() or {}
    text_value = data.get("text", "")
    lang = data.get("lang")
    editor = data.get("editor")
    tags = data.get("tags")

    service = get_service()
    result = service.create_alternative(text_value, lang=lang, editor=editor, tags=tags)

    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/agent", methods=["POST"])
def api_agent():
    """Invoke an LLM agent to analyze propositions using AI.

    Supports four types of AI analysis:
    - comment: Generate commentary on a single proposition
    - comparison: Compare multiple propositions
    - websearch: Search web for context (future feature)
    - reference: Find related propositions (future feature)

    The agent uses OpenAI's GPT models to provide philosophical analysis
    and insights based on the text content and structure.

    Request JSON:
        action (str): The agent action (comment, comparison, websearch, reference)
        targets (list[str], optional): List of proposition names to analyze
        language (str, optional): Language code for response ("de", "en", etc.)
        user_input (str, optional): Additional user prompt to guide the analysis

    Returns:
        JSON response with AI-generated analysis or error message

    Example:
        {"action": "comment", "targets": ["1.1"], "language": "en"}
    """
    data = request.get_json() or {}
    action = data.get("action", "").strip()
    targets = data.get("targets", [])
    language = data.get("language", "").strip()
    user_input = data.get("user_input", "").strip()

    # Validate that an action was specified
    if not action:
        return jsonify({"success": False, "error": "Action required"})

    service = get_service()
    # Invoke the LLM agent with the specified action and parameters
    result = service.agent(
        action,
        targets if targets else None,  # Use current proposition if no targets
        language=language or None,      # Use config default if not specified
        user_input=user_input or None,  # Optional user guidance
    )

    # Return error if agent invocation failed
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})

    return jsonify({"success": True, "data": result})


@app.route("/api/config", methods=["GET"])
def api_config_get():
    """Get current configuration."""
    service = get_service()
    config = service.config.list_preferences()
    return jsonify({"success": True, "data": config})


@app.route("/api/config/set", methods=["POST"])
def api_config_set():
    """Update a user configuration preference with type conversion and validation.

    Accepts string values from the web client and converts them to the appropriate
    type based on the default preference value. Validates the converted value
    before persisting to ~/.trclirc.

    Request JSON:
        key (str): Preference name (e.g., "lang", "display_length")
        value (str): Value as string (will be converted to correct type)

    Returns:
        JSON response with updated preference or error message

    Example:
        {"key": "display_length", "value": "500"}
    """
    data = request.get_json() or {}
    key = data.get("key", "").strip()
    value_str = data.get("value", "")

    # Validate that a key was provided
    if not key:
        return jsonify({"success": False, "error": "Key required"})

    service = get_service()
    config = service.config

    # Type conversion based on default value type
    try:
        # Get the default value to infer the expected type
        default_value = config.DEFAULT_PREFERENCES.get(key)
        if default_value is None:
            return jsonify({"success": False, "error": f"Unknown preference: {key}"})

        # Convert string input to the appropriate type
        expected_type = type(default_value)
        if expected_type == int:
            # Convert to integer (e.g., display_length, tree_max_depth)
            value = int(value_str)
        elif expected_type == bool:
            # Convert to boolean (accept multiple formats)
            value = value_str.lower() in ("true", "1", "yes", "on")
        else:
            # Keep as string (e.g., lang)
            value = value_str

        # Validate the converted value (checks ranges, valid options, etc.)
        is_valid, error_msg = config.validate_preference(key, value)
        if not is_valid:
            return jsonify({"success": False, "error": error_msg})

        # Persist the preference to ~/.trclirc
        config.set(key, value)
        service.record_config_update(key)
        return jsonify({"success": True, "data": {"key": key, "value": value}})
    except ValueError as e:
        return jsonify({"success": False, "error": f"Invalid value: {e}"})


@app.route("/api/help", methods=["GET"])
def api_help():
    """Get API documentation."""
    return jsonify({
        "success": True,
        "data": {
            "commands": {
                "get": {"method": "POST", "params": {"key": "proposition name or id:N"}, "description": "Navigate to proposition"},
                "parent": {"method": "POST", "params": {}, "description": "Go to parent"},
                "next": {"method": "POST", "params": {}, "description": "Go to next proposition"},
                "previous": {"method": "POST", "params": {}, "description": "Go to previous proposition"},
                "children": {"method": "POST", "params": {}, "description": "List children of current"},
                "list": {"method": "POST", "params": {"target": "optional"}, "description": "List children"},
                "tree": {"method": "POST", "params": {"target": "optional"}, "description": "Get tree view"},
                "search": {"method": "POST", "params": {"term": "search string"}, "description": "Search propositions"},
                "translations": {"method": "POST", "params": {}, "description": "Get translations"},
                "translate": {"method": "POST", "params": {"lang": "language code"}, "description": "Get specific translation"},
                "agent": {"method": "POST", "params": {"action": "comment|comparison|websearch|reference", "targets": "list of proposition names"}, "description": "Invoke LLM agent"},
                "config": {"method": "GET", "params": {}, "description": "Get config"},
                "config/set": {"method": "POST", "params": {"key": "preference", "value": "value"}, "description": "Set preference"},
            }
        }
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"success": False, "error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"success": False, "error": "Internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
