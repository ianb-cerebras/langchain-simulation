from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback
from typing import Dict, List, Any, Union, Optional, Tuple
from backend.uxr_logic import execute_research

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _extract_insights_from_synthesis(synthesis_text: str, research_question: str) -> Dict[str, str]:
    """Parse the synthesis text into concise dashboard fields."""
    insights = {
        "keyInsights": "",
        "observations": "",
        "takeaways": "",
    }

    if not synthesis_text:
        return {
            "keyInsights": f"Analysis completed for: {research_question}",
            "observations": "Multiple perspectives gathered from diverse participants",
            "takeaways": "Further analysis recommended based on initial findings",
        }

    lines = synthesis_text.split("\n")
    current_section: Optional[str] = None
    section_content: List[str] = []

    def _commit():
        nonlocal section_content, current_section
        if current_section and section_content:
            first_two = ". ".join([s for s in section_content if s][:2]).strip()
            if first_two and not first_two.endswith("."):
                first_two += "."
            insights[current_section] = first_two
        section_content = []

    for raw in lines:
        line = raw.strip()
        upper = line.upper()
        if not line:
            continue
        if "KEY THEMES" in upper or "THEMES" in upper:
            _commit()
            current_section = "keyInsights"
            continue
        if "DIVERSE PERSPECTIVES" in upper or "PERSPECTIVES" in upper:
            _commit()
            current_section = "observations"
            continue
        if "ACTIONABLE RECOMMENDATIONS" in upper or "RECOMMENDATIONS" in upper or "PAIN POINTS" in upper:
            _commit()
            current_section = "takeaways"
            continue

        # Clean bullets/numbers
        cleaned = line
        if cleaned.startswith(("- ", "* ", "• ")):
            cleaned = cleaned[2:].strip()
        elif len(cleaned) > 2 and cleaned[0].isdigit() and cleaned[1:3] == ". ":
            cleaned = cleaned[3:].strip()
        section_content.append(cleaned)

    _commit()

    # Ensure all fields populated
    if not insights["keyInsights"]:
        insights["keyInsights"] = synthesis_text.split(".")[0].strip() + "."
    if not insights["observations"]:
        insights["observations"] = "Participants showed varied perspectives based on their backgrounds and experiences."
    if not insights["takeaways"]:
        insights["takeaways"] = "Consider implementing changes based on user feedback and identified patterns."

    return insights


def _format_participants(personas: Union[List[Dict[str, Any]], List[Any]], audience: str, all_interviews: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Convert personas and interviews to dashboard participant rows."""
    participants: List[Dict[str, Any]] = []
    safe_interviews = all_interviews or []
    for i, p in enumerate(personas or []):
        # Handle pydantic or dict
        pd = p.model_dump() if hasattr(p, "model_dump") else p
        row: Dict[str, Any] = {
            "id": i + 1,
            "header": pd.get("name", f"Participant {i+1}"),
            "type": audience,
            "status": ", ".join(pd.get("traits", [])) if pd.get("traits") else "",
            "target": str(pd.get("age", "")),
            "limit": pd.get("job", ""),
        }
        if i < len(safe_interviews):
            inter = safe_interviews[i]
            ip = inter.get("persona")
            if hasattr(ip, "model_dump"):
                ip = ip.model_dump()
            row["interview"] = {
                "persona": ip,
                "responses": inter.get("responses", []),
            }
        participants.append(row)
    return participants

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
        # Execute the real workflow using ported logic
        data = execute_research(
            research_question=question,
            target_demographic=audience,
            num_interviews=num_interviews,
            num_questions=num_questions,
            cerebras_api_key=cerebras_api_key,
        )

        # Transform for dashboard compatibility
        synthesis = data.get("synthesis", "") if isinstance(data, dict) else ""
        insights = _extract_insights_from_synthesis(synthesis, question)
        personas = data.get("personas", []) if isinstance(data, dict) else []
        all_interviews = data.get("all_interviews", []) if isinstance(data, dict) else []
        participants = _format_participants(personas, audience, all_interviews)

        transformed = {
            **data,
            **insights,
            "participants": participants,
        }

        return jsonify({"success": True, "data": transformed})
    except Exception as e:
        traceback.print_exc()
        # Include a structured error response with request context for debugging
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "context": {
                        "question_len": len(question),
                        "audience_len": len(audience),
                        "num_interviews": num_interviews,
                        "num_questions": num_questions,
                    },
                    "hint": "Enable UXR_DEBUG=1 to log normalization steps on the backend",
                }
            ),
            500,
        )

@app.get("/api/health")
def health() -> Tuple[str, int]:
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


