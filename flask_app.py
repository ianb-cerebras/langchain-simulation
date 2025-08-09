#!/usr/bin/env python3
"""
Flask backend for running UXR simulations
Incorporates code from UXR.py with minimal changes
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import sys
import time
from datetime import datetime
import traceback
from typing import Dict, List, TypedDict

# Core imports from UXR.py (removing IPython dependencies)
from langchain_cerebras import ChatCerebras
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field, ValidationError

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ============= START OF UXR.py CODE =============
# Configuration Constants
DEFAULT_NUM_INTERVIEWS = 10
DEFAULT_NUM_QUESTIONS = 5

# Set up API keys from environment
os.environ["CEREBRAS_API_KEY"] = os.environ.get("CEREBRAS_API_KEY", "")
os.environ["LANGCHAIN_TRACING_V2"] = "false"  # Disable LangSmith tracing

# Initialize LLM
llm = ChatCerebras(model="llama3.3-70b", temperature=0.7, max_tokens=800)

# General model instructions
system_prompt = """You are a helpful assistant. Provide a direct, clear response without showing your thinking process. Respond directly without using <think> tags or showing internal reasoning."""

def ask_ai(prompt: str) -> str:
    """Send prompt to Cerebras AI and return response"""
    response = llm.invoke([{"role":"system", "content": system_prompt},{"role": "user", "content": prompt}])
    return response.content

# Data Models
class Persona(BaseModel):
    name: str = Field(..., description="Full name of the persona")
    age: int = Field(..., description="Age in years")
    job: str = Field(..., description="Job title or role")
    traits: List[str] = Field(..., description="3-4 personality traits")
    communication_style: str = Field(..., description="How this person communicates")
    background: str = Field(..., description="One background detail shaping their perspective")

class PersonasList(BaseModel):
    personas: List[Persona] = Field(..., description="List of generated personas")

class Questions(BaseModel):
    questions: List = Field(..., description="List of interview questions")

# State Definition
class InterviewState(TypedDict):
    # Configuration inputs
    research_question: str
    target_demographic: str
    num_interviews: int
    num_questions: int
    
    # Generated data
    interview_questions: List[str]
    personas: List[Persona]
    
    # Current interview tracking
    current_persona_index: int
    current_question_index: int
    current_interview_history: List[Dict]
    
    # Results storage
    all_interviews: List[Dict]
    synthesis: str

# Prompt Templates (copied from UXR.py)
question_gen_prompt = """Generate exactly {num_questions} interview questions about: {research_question}. Use the provided structured output to format the questions."""

persona_prompt = (
    "Generate exactly {num_personas} unique personas for an interview. "
    "Each should belong to the target demographic: {demographic}. "
    "Respond only in JSON using this format: {{ personas: [ ... ] }}"
)

interview_prompt = """You are {persona_name}, a {persona_age}-year-old {persona_job} who is {persona_traits}.
Answer the following question in 2-3 sentences:

Question: {question}

Answer as {persona_name} in your own authentic voice. Be brief but creative and unique, and make each answer conversational.
BE REALISTIC – do not be overly optimistic. Mimic real human behavior based on your persona, and give honest answers."""

synthesis_prompt_template = """Analyze these {num_interviews} user interviews about "{research_question}" among {target_demographic} and concise yet comprehensive analysis:

1. KEY THEMES: What patterns and common themes emerged across all interviews? Look for similarities in responses, shared concerns, and recurring topics.

2. DIVERSE PERSPECTIVES: What different viewpoints or unique insights did different personas provide? Highlight contrasting opinions or approaches.

3. PAIN POINTS & OPPORTUNITIES: What challenges, frustrations, or unmet needs were identified? What opportunities for improvement emerged?

4. ACTIONABLE RECOMMENDATIONS: Based on these insights, what specific actions should be taken? Provide concrete, implementable suggestions.

Keep the analysis thorough but well-organized and actionable.

Interview Data:
{interview_summary}
"""

# Node Functions (copied from UXR.py, simplified without follow-ups)
def configuration_node(state: InterviewState) -> Dict:
    """Get user inputs and generate interview questions"""
    structured_llm = llm.with_structured_output(Questions)
    questions = structured_llm.invoke(
        question_gen_prompt.format(
            num_questions=state['num_questions'],
            research_question=state['research_question']
        )
    )
    questions = questions.questions
    
    return {
        "num_questions": state['num_questions'],
        "num_interviews": state['num_interviews'],
        "interview_questions": questions
    }

def persona_generation_node(state: InterviewState) -> Dict:
    """Generate diverse user personas"""
    num_personas = state['num_interviews']
    demographic = state['target_demographic']
    max_retries = 5
    
    structured_llm = llm.with_structured_output(PersonasList)
    
    for attempt in range(max_retries):
        try:
            raw_output = structured_llm.invoke([{
                "role": "user", 
                "content": persona_prompt.format(
                    num_personas=num_personas, 
                    demographic=demographic
                )
            }])
            
            if raw_output is None:
                raise ValueError("LLM returned None")
            
            validated = PersonasList.model_validate(raw_output)
            
            if len(validated.personas) != num_personas:
                raise ValueError(f"Expected {num_personas} personas, got {len(validated.personas)}")
            
            return {
                "personas": validated.personas,
                "current_persona_index": 0,
                "current_question_index": 0,
                "all_interviews": []
            }
            
        except (ValidationError, ValueError, TypeError) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to generate personas after {max_retries} attempts: {e}")

def interview_node(state: InterviewState) -> Dict:
    """Conduct interview with current persona (simplified without follow-ups)"""
    persona_idx = state['current_persona_index']
    question_idx = state['current_question_index']
    
    print(f"  Interview: Persona {persona_idx + 1}/{len(state['personas'])}, Question {question_idx + 1}/{len(state['interview_questions'])}")
    
    persona = state['personas'][persona_idx]
    question = state['interview_questions'][question_idx]
    
    # Generate main answer
    prompt = interview_prompt.format(
        persona_name=persona.name,
        persona_age=persona.age,
        persona_job=persona.job,
        persona_traits=persona.traits,
        question=question
    )
    answer = ask_ai(prompt)
    
    # Update history
    history = state.get('current_interview_history', []) + [{
        "question": question,
        "answer": answer
    }]
    
    # If last question for this persona, save interview & advance to next persona
    if state['current_question_index'] + 1 >= len(state['interview_questions']):
        return {
            "all_interviews": state['all_interviews'] + [{
                'persona': persona,
                'responses': history
            }],
            "current_interview_history": [],
            "current_question_index": 0,
            "current_persona_index": state['current_persona_index'] + 1
        }
    
    # Continue with next question for same persona
    return {
        "current_interview_history": history,
        "current_question_index": state['current_question_index'] + 1
    }

def synthesis_node(state: InterviewState) -> Dict:
    """Synthesize insights from all interviews"""
    
    # Compile all responses
    interview_summary = f"Research Question: {state['research_question']}\n"
    interview_summary += f"Target Demographic: {state['target_demographic']}\n"
    interview_summary += f"Number of Interviews: {len(state['all_interviews'])}\n\n"
    
    for i, interview in enumerate(state['all_interviews'], 1):
        p = interview['persona']
        interview_summary += f"Interview {i} - {p.name} ({p.age}, {p.job}):\n"
        interview_summary += f"Persona Traits: {p.traits}\n"
        for j, qa in enumerate(interview['responses'], 1):
            interview_summary += f"Q{j}: {qa['question']}\n"
            interview_summary += f"A{j}: {qa['answer']}\n"
        interview_summary += "\n"
    
    prompt = synthesis_prompt_template.format(
        num_interviews=len(state['all_interviews']),
        research_question=state['research_question'],
        target_demographic=state['target_demographic'],
        interview_summary=interview_summary
    )
    
    try:
        synthesis = ask_ai(prompt)
    except Exception as e:
        synthesis = f"Error during synthesis: {e}\n\nRaw interview data available for manual analysis."
    
    return {"synthesis": synthesis}

# Router Function
def interview_router(state: InterviewState) -> str:
    """Route between continuing interviews or ending"""
    if state['current_persona_index'] >= len(state['personas']):
        return "synthesize"
    else:
        return "interview"

# Workflow Builder (copied from UXR.py)
def build_interview_workflow():
    """Build the complete interview workflow graph"""
    workflow = StateGraph(InterviewState)
    
    # Add all our specialized nodes
    workflow.add_node("config", configuration_node)
    workflow.add_node("personas", persona_generation_node)
    workflow.add_node("interview", interview_node)
    workflow.add_node("synthesize", synthesis_node)
    
    # Define the workflow connections
    workflow.set_entry_point("config")
    workflow.add_edge("config", "personas")
    workflow.add_edge("personas", "interview")
    
    # Conditional routing based on interview progress
    workflow.add_conditional_edges(
        "interview",
        interview_router,
        {
            "interview": "interview",    # Continue interviewing
            "synthesize": "synthesize"   # All done, analyze results
        }
    )
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()

# ============= END OF UXR.py CODE =============

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/run-uxr', methods=['POST'])
def run_uxr():
    """Run UXR simulation with provided parameters"""
    try:
        data = request.json
        
        # Extract parameters
        research_question = data.get('question', '')
        target_demographic = data.get('audience', '')
        num_interviews = int(data.get('numInterviews', 5))
        num_questions = int(data.get('numQuestions', 3))
        
        # Validate inputs
        if not research_question:
            return jsonify({"error": "Research question is required"}), 400
        if not target_demographic:
            return jsonify({"error": "Target demographic is required"}), 400
        
        print(f"Starting UXR simulation:")
        print(f"  Research Question: {research_question}")
        print(f"  Target Demographic: {target_demographic}")
        print(f"  Number of Interviews: {num_interviews}")
        print(f"  Number of Questions: {num_questions}")
        
        # Build and run the workflow
        workflow = build_interview_workflow()
        
        # Initialize state
        initial_state = {
            "research_question": research_question,
            "target_demographic": target_demographic,
            "num_interviews": num_interviews,
            "num_questions": num_questions,
            "interview_questions": [],
            "personas": [],
            "current_persona_index": 0,
            "current_question_index": 0,
            "current_interview_history": [],
            "all_interviews": [],
            "synthesis": ""
        }
        
        # Run the workflow with recursion limit
        print("Running workflow...")
        start_time = time.time()
        
        # Set a higher recursion limit to handle the workflow
        # Each persona * each question = total interview nodes
        # Add extra buffer for config, persona generation, and synthesis nodes
        expected_recursions = (num_interviews * num_questions) + 20  
        config = {"recursion_limit": max(expected_recursions, 100)}
        
        print(f"  Expected recursions: {expected_recursions}, Setting limit to: {config['recursion_limit']}")
        
        final_state = workflow.invoke(initial_state, config=config)
        elapsed_time = time.time() - start_time
        print(f"✅ Workflow completed in {elapsed_time:.1f} seconds")
        
        # Parse synthesis to extract insights
        synthesis = final_state.get("synthesis", "")
        sections = {
            "keyInsights": "",
            "observations": "",
            "takeaways": ""
        }
        
        if synthesis:
            lines = synthesis.split("\n")
            current_section = ""
            collecting_content = False
            
            for line in lines:
                upper_line = line.upper()
                stripped_line = line.strip()
                
                # Check for section headers (handles both ### headers and numbered sections)
                if "KEY THEMES" in upper_line:
                    current_section = "keyInsights"
                    collecting_content = True
                    continue
                elif "DIVERSE PERSPECTIVES" in upper_line:
                    current_section = "observations"
                    collecting_content = True
                    continue
                elif "PAIN POINTS" in upper_line or "OPPORTUNITIES" in upper_line:
                    current_section = "painPoints"
                    collecting_content = True
                    continue
                elif "ACTIONABLE RECOMMENDATIONS" in upper_line or "RECOMMENDATIONS" in upper_line:
                    current_section = "takeaways"
                    collecting_content = True
                    continue
                
                # Skip empty lines and markdown headers
                if not stripped_line or stripped_line.startswith("#"):
                    continue
                
                # Collect content for current section
                if collecting_content and current_section:
                    # Clean up bullet points and numbers
                    content = stripped_line
                    if content.startswith(("- ", "* ", "• ")):
                        content = content[2:].strip()
                    elif len(content) > 2 and content[0].isdigit() and content[1:3] == ". ":
                        content = content[3:].strip()
                    
                    # Add to appropriate section
                    if current_section == "keyInsights":
                        sections["keyInsights"] += ("; " if sections["keyInsights"] else "") + content
                    elif current_section == "observations":
                        sections["observations"] += ("; " if sections["observations"] else "") + content
                    elif current_section in ["takeaways", "painPoints"]:
                        sections["takeaways"] += ("; " if sections["takeaways"] else "") + content
        
        # Transform personas into participant format
        personas_data = []
        for persona in final_state.get("personas", []):
            # Convert Pydantic model to dict if necessary
            if hasattr(persona, 'model_dump'):
                persona_dict = persona.model_dump()
            else:
                persona_dict = dict(persona)
            personas_data.append(persona_dict)
        
        participants = []
        all_interviews = final_state.get("all_interviews", [])
        
        for index, persona_dict in enumerate(personas_data):
            # Find corresponding interview
            interview = None
            if index < len(all_interviews):
                interview_data = all_interviews[index]
                # Convert persona in interview to dict
                interview_persona = interview_data["persona"]
                if hasattr(interview_persona, 'model_dump'):
                    interview_persona = interview_persona.model_dump()
                
                interview = {
                    "persona": interview_persona,
                    "responses": interview_data["responses"]
                }
            
            participants.append({
                "id": index + 1,
                "header": persona_dict.get("name", "Unknown"),
                "type": target_demographic,
                "status": ", ".join(persona_dict.get("traits", [])),
                "target": str(persona_dict.get("age", "")),
                "limit": persona_dict.get("job", "N/A"),
                "interview": interview
            })
        
        # Prepare response (similar to save_research_results from UXR.py)
        result = {
            "research_question": research_question,
            "target_demographic": target_demographic,
            "timestamp": datetime.now().isoformat(),
            "num_interviews": num_interviews,
            "num_questions": num_questions,
            "interview_questions": final_state.get("interview_questions", []),
            "personas": personas_data,
            "all_interviews": [
                {
                    "persona": interview["persona"].model_dump() if hasattr(interview["persona"], 'model_dump') else interview["persona"],
                    "responses": interview["responses"]
                }
                for interview in all_interviews
            ],
            "synthesis": synthesis,
            "keyInsights": sections["keyInsights"],
            "observations": sections["observations"],
            "takeaways": sections["takeaways"],
            "participants": participants
        }
        
        # Save result to file for Next.js to read
        with open("uxr-result.json", "w", encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print("✅ UXR simulation completed successfully")
        print(f"💾 Results saved to: uxr-result.json")
        
        return jsonify({"success": True, "data": result})
        
    except Exception as e:
        print(f"❌ Error in UXR simulation: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == '__main__':
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Check if API key is set
    api_key = os.environ.get('CEREBRAS_API_KEY')
    if not api_key:
        print("⚠️  Warning: CEREBRAS_API_KEY not set")
        print("   Please set your API key in the .env file or environment variables")
    
    print(f"🚀 Starting Flask server on port {port}")
    print("✅ Setup complete")
    app.run(debug=True, port=port, host='0.0.0.0')