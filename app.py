"""Flask web wrapper for Tractatus CLI."""
from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import os
from tractatus_config import TrcliConfig
from tractatus_orm.database import SessionLocal, init_db
from tractatus_service import TractatusService

# Initialize Flask app
app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# Initialize database
init_db()

# Global service instance (one per session)
_service_cache: dict[str, TractatusService] = {}


def get_service() -> TractatusService:
    """Get or create service instance for current session."""
    # For simplicity, use a single shared service
    # In production, you'd want per-user sessions
    if "default" not in _service_cache:
        session = SessionLocal()
        config = TrcliConfig()
        _service_cache["default"] = TractatusService(session, config)
    return _service_cache["default"]


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
    """Navigate to proposition by name or id."""
    data = request.get_json() or {}
    key = data.get("key", "").strip()

    if not key:
        return jsonify({"success": False, "error": "Key required"})

    service = get_service()
    result = service.get(key)

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


@app.route("/api/agent", methods=["POST"])
def api_agent():
    """Invoke LLM agent.

    Request JSON:
        action: str - The agent action (comment, comparison, websearch, reference)
        targets: list[str] - Optional list of proposition names
        language: str - Optional language code ("de" or "en")
    """
    data = request.get_json() or {}
    action = data.get("action", "").strip()
    targets = data.get("targets", [])
    language = data.get("language", "").strip()

    if not action:
        return jsonify({"success": False, "error": "Action required"})

    service = get_service()
    result = service.agent(
        action, targets if targets else None, language=language or None
    )

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
    """Set configuration preference."""
    data = request.get_json() or {}
    key = data.get("key", "").strip()
    value_str = data.get("value", "")

    if not key:
        return jsonify({"success": False, "error": "Key required"})

    service = get_service()
    config = service.config

    # Type conversion
    try:
        default_value = config.DEFAULT_PREFERENCES.get(key)
        if default_value is None:
            return jsonify({"success": False, "error": f"Unknown preference: {key}"})

        expected_type = type(default_value)
        if expected_type == int:
            value = int(value_str)
        elif expected_type == bool:
            value = value_str.lower() in ("true", "1", "yes", "on")
        else:
            value = value_str

        # Validate
        is_valid, error_msg = config.validate_preference(key, value)
        if not is_valid:
            return jsonify({"success": False, "error": error_msg})

        # Set it
        config.set(key, value)
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
