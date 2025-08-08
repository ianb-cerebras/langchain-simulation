#!/usr/bin/env python3
import json
import os
import sys

def main():
    # Get inputs from environment variables
    question = os.getenv("UXR_QUESTION", "How do users feel about product changes?")
    audience = os.getenv("UXR_AUDIENCE", "General users")
    num_interviews = int(os.getenv("UXR_NUM_INTERVIEWS", "10"))
    
    # Simple mock research results (replace with actual Cerebras API call)
    results = {
        "keyInsights": f"Users in the {audience} segment showed mixed reactions to: {question}",
        "observations": f"Focus groups with {num_interviews} participants revealed trust and familiarity concerns.",
        "takeaways": f"Brand consistency matters more to {audience} than radical visual changes."
    }
    
    # Output JSON for the API to consume
    print(json.dumps(results, indent=2))
    print("✅ Research simulation complete", file=sys.stderr)

if __name__ == "__main__":
    main()