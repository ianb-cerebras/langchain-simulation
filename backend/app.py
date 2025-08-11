from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback
from backend.uxr_logic import execute_research

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.route("/api/run-uxr", methods=["POST"])
def run_uxr():
    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "")
    audience = payload.get("audience", "")
    num_interviews = int(payload.get("numInterviews", 5))
    num_questions = int(payload.get("numQuestions", 3))
    cerebras_api_key = payload.get("cerebrasApiKey") or payload.get("cerebras_api_key")

    if not cerebras_api_key:
        return (
            jsonify({"success": False, "error": "Missing cerebrasApiKey"}),
            400,
        )

    try:
        # Execute the real workflow using ported logic (no changes to core processing)
        data = execute_research(
            research_question=question,
            target_demographic=audience,
            num_interviews=num_interviews,
            num_questions=num_questions,
            cerebras_api_key=cerebras_api_key,
        )
        return jsonify({"success": True, "data": data})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.get("/api/health")
def health() -> tuple[str, int]:
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


