#!/usr/bin/env python3
import json
import os
import sys
from typing import List, Dict, Any

# Set the API key from the working example
os.environ["CEREBRAS_API_KEY"] = "REMOVED"

try:
    from langchain_cerebras import ChatCerebras
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    import requests

def call_cerebras_api(prompt: str, api_key: str) -> str:
    """Call Cerebras API using LangChain or fallback to HTTP"""
    if LANGCHAIN_AVAILABLE:
        try:
            llm = ChatCerebras(model="llama3.3-70b", temperature=0.7, max_tokens=800)
            response = llm.invoke([{"role": "user", "content": f"You are a helpful assistant. Provide a direct, clear response without showing your thinking process. {prompt}"}])
            return response.content
        except Exception as e:
            print(f"⚠️ LangChain error: {e}", file=sys.stderr)
    
    # Fallback to HTTP
    url = "https://api.cerebras.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3.1-8b",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Provide direct, clear responses without showing thinking process."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"API Error: {str(e)}"

def generate_personas(question: str, audience: str, num_personas: int, api_key: str) -> List[Dict]:
    """Generate diverse user personas for the research"""
    prompt = f"""Generate exactly {num_personas} diverse user personas for researching: "{question}"
Target audience: {audience}

Create realistic, detailed personas with varied backgrounds that would have different perspectives on this topic. Consider different:
- Demographics (age, location, income level)
- Psychographics (values, interests, lifestyle)
- Relevant experiences that would influence their opinion
- Cultural backgrounds and contexts

Return ONLY a JSON array with this exact structure:
[
  {{
    "name": "First Last",
    "age": 22,
    "job": "Job Title", 
    "traits": ["trait1", "trait2", "trait3"],
    "communication_style": "casual/formal/enthusiastic/skeptical etc",
    "background": "relevant detail that influences their perspective on the research topic"
  }}
]

Make each persona unique with different ages (spread across the {audience} range), varied jobs, distinct personalities, and backgrounds that would lead to diverse opinions about: {question}"""

    response = call_cerebras_api(prompt, api_key)
    
    try:
        # Try to extract JSON from response
        if '{' in response:
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                personas = json.loads(json_str)
                if isinstance(personas, list) and len(personas) > 0:
                    return personas[:num_personas]
        
        # If that fails, try parsing the whole response
        personas = json.loads(response)
        if isinstance(personas, list) and len(personas) > 0:
            return personas[:num_personas]
            
    except Exception as e:
        print(f"⚠️  Persona generation failed: {e}", file=sys.stderr)
        
    # Enhanced fallback personas based on the research question
    fallback_personas = generate_fallback_personas(question, audience, num_personas)
    
    return fallback_personas[:num_personas]

def generate_interview_questions(question: str, num_questions: int, api_key: str) -> List[str]:
    """Generate interview questions for the research"""
    prompt = f"""Generate exactly {num_questions} interview questions about: "{question}"

Requirements:
- Each question must be open-ended (not yes/no)
- Keep questions conversational and clear
- Focus on understanding user feelings, motivations, and experiences
- Return as JSON array of strings"""

    response = call_cerebras_api(prompt, api_key)
    
    try:
        questions = json.loads(response)
        return questions if isinstance(questions, list) else []
    except:
        # Fallback questions
        return [
            f"How do you feel about {question}?",
            "What concerns or excitement does this bring up for you?",
            "How might this impact your daily routine?"
        ][:num_questions]

def simulate_interview(persona: Dict, questions: List[str], research_question: str, api_key: str) -> List[Dict]:
    """Simulate an interview with a persona"""
    interview_responses = []
    
    for question in questions:
        prompt = f"""You are {persona['name']}, age {persona['age']}, working as {persona['job']}.
Your traits: {', '.join(persona.get('traits', []))}
Communication style: {persona.get('communication_style', 'casual')}
Background: {persona.get('background', 'general user')}

You're being interviewed about: "{research_question}"

Question: {question}

Respond naturally as this character would, in 1-2 sentences. Be authentic to their personality and background."""

        response = call_cerebras_api(prompt, api_key)
        
        interview_responses.append({
            "question": question,
            "response": response,
            "persona_name": persona['name']
        })
    
    return interview_responses

def synthesize_insights(all_interviews: List[Dict], research_question: str, api_key: str) -> Dict[str, str]:
    """Synthesize all interview data into key insights"""
    
    # Prepare interview data for analysis
    interview_summary = ""
    for interview in all_interviews:
        interview_summary += f"\nParticipant: {interview.get('persona_name', 'Unknown')}\n"
        for qa in interview.get('responses', []):
            interview_summary += f"Q: {qa['question']}\nA: {qa['response']}\n"
    
    synthesis_prompt = f"""Analyze these user research interviews about: "{research_question}"

Interview Data:
{interview_summary}

Provide insights in exactly this JSON format:
{{
  "keyInsights": "One sentence summarizing the main finding",
  "observations": "One sentence about specific patterns or behaviors observed", 
  "takeaways": "One sentence about actionable recommendations"
}}"""

    response = call_cerebras_api(synthesis_prompt, api_key)
    
    try:
        insights = json.loads(response)
        return insights
    except:
        # Fallback insights
        return {
            "keyInsights": f"Users showed varied reactions to the research question: {research_question}",
            "observations": f"Participants expressed both concerns and interest based on their backgrounds",
            "takeaways": f"Consider user diversity when implementing changes related to {research_question}"
        }

def main():
    """Main research simulation function"""
    
    # Get inputs from environment variables
    question = os.getenv("UXR_QUESTION", "How do users feel about product changes?")
    audience = os.getenv("UXR_AUDIENCE", "General users") 
    num_interviews = int(os.getenv("UXR_NUM_INTERVIEWS", "3"))
    
    # Use the hardcoded API key or environment variable
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("⚠️ Using fallback responses - CEREBRAS_API_KEY not found", file=sys.stderr)
    
    print("🚀 Starting user research simulation...", file=sys.stderr)
    
    # Generate personas
    print(f"👥 Generating {num_interviews} personas...", file=sys.stderr)
    personas = generate_personas(question, audience, num_interviews, api_key)
    
    # Generate interview questions  
    print("❓ Creating interview questions...", file=sys.stderr)
    questions = generate_interview_questions(question, 3, api_key)
    
    # Conduct interviews
    all_interviews = []
    for i, persona in enumerate(personas[:num_interviews]):
        print(f"🎤 Interviewing {persona.get('name', f'Participant {i+1}')}...", file=sys.stderr)
        responses = simulate_interview(persona, questions, question, api_key)
        all_interviews.append({
            "persona_name": persona.get('name', f'Participant {i+1}'),
            "responses": responses
        })
    
    # Synthesize insights
    print("🔍 Analyzing results...", file=sys.stderr)
    insights = synthesize_insights(all_interviews, question, api_key)
    
    # Prepare participant data for the dashboard table
    participants = []
    for i, persona in enumerate(personas[:num_interviews]):
        participants.append({
            "id": i + 1,
            "header": persona.get('name', f'Participant {i+1}'),
            "type": audience,
            "status": ', '.join(persona.get('traits', ['Unknown'])[:2]),
            "target": str(persona.get('age', 25)),
            "limit": persona.get('job', 'Unknown')
        })
    
    # Combine insights with participant data
    result = {
        **insights,
        "participants": participants
    }
    
    # Output results as JSON
    print(json.dumps(result, indent=2))
    print("✅ Research simulation complete", file=sys.stderr)

if __name__ == "__main__":
    main()