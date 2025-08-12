from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback
import re
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
            # Only set the section once to avoid accidental overwrites/doubling
            if not insights.get(current_section):
                insights[current_section] = first_two
        section_content = []

    def _sanitize(text: str) -> str:
        # Remove bold/italic markdown and trailing duplicate punctuation
        cleaned = text.replace("**", "").replace("__", "")
        cleaned = cleaned.strip()
        # Collapse repeated terminal punctuation like '..' or '!!'
        while cleaned.endswith("..") or cleaned.endswith("!!") or cleaned.endswith("??"):
            cleaned = cleaned[:-1]
        return cleaned

    def _detect_section_and_remainder(line: str) -> Tuple[Optional[str], Optional[str]]:
        """Return (section_key, remainder_after_colon) if the line appears to start a section.
        Supports multiple synonymous headings and inline content after a colon."""
        stripped = line.strip()
        if not stripped:
            return None, None
        upper = stripped.upper()

        key_markers = [
            "KEY THEMES",
            "THEMES",
            "KEY INSIGHTS",
            "INSIGHTS",
            "INSIGHT SUMMARY",
        ]
        obs_markers = [
            "DIVERSE PERSPECTIVES",
            "PERSPECTIVES",
            "OBSERVATIONS",
            "POINTS OF OBSERVATION",
            "POINTS OF OBSERVATIONS",
            "OBSERVATION POINTS",
        ]
        # Route pain/opportunities to observations (to avoid doubling with takeaways)
        pain_markers = [
            "PAIN POINTS & OPPORTUNITIES",
            "PAIN POINTS",
            "OPPORTUNITIES",
        ]
        # Only true takeaways/recommendations map to takeaways
        recommendation_markers = [
            "ACTIONABLE RECOMMENDATIONS",
            "RECOMMENDATIONS",
            "KEY TAKEAWAYS",
            "TAKEAWAYS",
            "BIG TAKEAWAYS",
        ]

        def find_match(markers: List[str]) -> bool:
            return any(m in upper for m in markers)

        section: Optional[str] = None
        if find_match(key_markers):
            section = "keyInsights"
        elif find_match(obs_markers) or find_match(pain_markers):
            section = "observations"
        elif find_match(recommendation_markers):
            section = "takeaways"

        if section is None:
            return None, None

        # Capture inline content after a colon, if present
        remainder: Optional[str] = None
        if ":" in stripped:
            remainder = stripped.split(":", 1)[1].strip()
        return section, remainder

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # Detect section headers (with synonyms) and optionally capture inline content
        detected_section, inline_remainder = _detect_section_and_remainder(line)
        if detected_section:
            _commit()
            current_section = detected_section
            if inline_remainder:
                cleaned_inline = _sanitize(inline_remainder)
                # Remove common bullet/number prefixes like "1. ", "- ", "• ", "1) "
                cleaned_inline = re.sub(r"^(?:[-*•]\s+|\d+[\.)]\s+)", "", cleaned_inline).strip()
                if cleaned_inline:
                    section_content.append(cleaned_inline)
            continue

        # Clean bullets/numbers and strip markdown emphasis for regular content lines
        cleaned = _sanitize(line)
        cleaned = re.sub(r"^(?:[-*•]\s+|\d+[\.)]\s+)", "", cleaned).strip()
        if cleaned:
            section_content.append(cleaned)

    _commit()

    # Ensure all fields populated
    if not insights["keyInsights"]:
        first = synthesis_text.split(".")[0].strip()
        insights["keyInsights"] = _sanitize(first + ".")
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


