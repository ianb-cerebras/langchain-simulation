from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.route("/api/run-uxr", methods=["POST"])
def run_uxr():
    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "")
    audience = payload.get("audience", "")
    num_interviews = int(payload.get("numInterviews", 5))
    num_questions = int(payload.get("numQuestions", 3))

    # Minimal synthetic data matching the frontend schema
    participants = [
        {
            "id": i + 1,
            "header": f"Participant {i + 1}",
            "type": str(audience or "Gen Z"),
            "status": "Active",
            "target": str(20 + (i % 10)),
            "limit": "N/A",
        }
        for i in range(num_interviews)
    ]

    all_interviews = [
        {
            "persona": {
                "name": f"Participant {i + 1}",
                "age": 20 + (i % 10),
                "job": "N/A",
                "traits": ["curious", "pragmatic"],
            },
            "responses": [
                {
                    "question": f"Q{j + 1}: {question or 'Your thoughts?'}",
                    "answer": f"Sample answer {j + 1} from participant {i + 1} about {audience or 'the topic' }.",
                }
                for j in range(num_questions)
            ],
        }
        for i in range(num_interviews)
    ]

    data = {
        "keyInsights": f"Users shared concise views on '{question or 'the question'}'.",
        "observations": f"Audience '{audience or 'General'}' highlighted a few consistent themes.",
        "takeaways": "Iterate with focused improvements and validate with small cohorts.",
        "num_interviews": num_interviews,
        "num_questions": num_questions,
        "participants": participants,
        "all_interviews": all_interviews,
    }

    return jsonify({"success": True, "data": data})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


