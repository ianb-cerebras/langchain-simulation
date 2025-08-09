#!/usr/bin/env python3
"""Test script to verify UXR.py JSON saving functionality"""

import json
import os
from datetime import datetime
from UXR import save_research_results, Persona

# Create test data
test_state = {
    "research_question": "How do users interact with AI assistants?",
    "target_demographic": "Software developers aged 25-40",
    "num_interviews": 2,
    "num_questions": 3,
    "interview_questions": [
        "How often do you use AI assistants?",
        "What tasks do you use them for?",
        "What improvements would you like to see?"
    ],
    "personas": [
        Persona(
            name="Alice Johnson",
            age=28,
            job="Frontend Developer",
            traits=["detail-oriented", "creative", "patient"],
            communication_style="Direct and technical",
            background="5 years in web development"
        ),
        Persona(
            name="Bob Smith",
            age=35,
            job="Backend Engineer",
            traits=["analytical", "pragmatic", "focused"],
            communication_style="Concise and logical",
            background="10 years in enterprise software"
        )
    ],
    "all_interviews": [
        {
            "persona": Persona(
                name="Alice Johnson",
                age=28,
                job="Frontend Developer",
                traits=["detail-oriented", "creative", "patient"],
                communication_style="Direct and technical",
                background="5 years in web development"
            ),
            "responses": [
                {"question": "How often do you use AI assistants?", "answer": "Daily for code reviews and debugging"},
                {"question": "What tasks do you use them for?", "answer": "Mainly for explaining complex code and generating boilerplate"},
                {"question": "What improvements would you like to see?", "answer": "Better understanding of project context"}
            ]
        },
        {
            "persona": Persona(
                name="Bob Smith",
                age=35,
                job="Backend Engineer",
                traits=["analytical", "pragmatic", "focused"],
                communication_style="Concise and logical",
                background="10 years in enterprise software"
            ),
            "responses": [
                {"question": "How often do you use AI assistants?", "answer": "Several times a week"},
                {"question": "What tasks do you use them for?", "answer": "Architecture decisions and performance optimization"},
                {"question": "What improvements would you like to see?", "answer": "More accurate technical recommendations"}
            ]
        }
    ],
    "synthesis": "Key findings: Developers use AI assistants regularly for code-related tasks..."
}

# Test the save function
print("Testing UXR JSON save functionality...")
filename = save_research_results(test_state, "test_uxr_output.json")

# Verify the file was created and contains valid JSON
if os.path.exists(filename):
    with open(filename, 'r') as f:
        loaded_data = json.load(f)
    
    print(f"✅ JSON file created successfully: {filename}")
    print(f"✅ Contains {len(loaded_data['personas'])} personas")
    print(f"✅ Contains {len(loaded_data['all_interviews'])} interviews")
    print(f"✅ Research question: {loaded_data['research_question']}")
    print("\nJSON structure verified successfully!")
else:
    print("❌ Failed to create JSON file")