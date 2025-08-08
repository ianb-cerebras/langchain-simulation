#!/usr/bin/env python3
"""
Core components extracted from UXR.py for reusable LangGraph workflow.
Preserves all original logic while removing Jupyter/IPython dependencies.
"""

import os
from typing import Dict, List, TypedDict
from pydantic import BaseModel, Field, ValidationError

from langchain_cerebras import ChatCerebras
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# Configuration Constants
DEFAULT_NUM_INTERVIEWS = 10
DEFAULT_NUM_QUESTIONS = 5

# Initialize LLM
os.environ.setdefault("CEREBRAS_API_KEY", "REMOVED")
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

# Prompt Templates
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

followup_question_prompt = """
Generate ONE natural follow‑up question for {persona_name} based on their last answer:
"{previous_answer}"
Keep it conversational and dig a bit deeper.
"""

followup_answer_prompt = """
You are {persona_name}, a {persona_age}-year-old {persona_job} who is {persona_traits}.

Answer the follow‑up question below in 2‑4 sentences, staying authentic and specific.

Follow‑up question: {followup_question}

Answer as {persona_name}:
"""

synthesis_prompt_template = """Analyze these {num_interviews} user interviews about "{research_question}" among {target_demographic} and concise yet comprehensive analysis:

1. KEY THEMES: What patterns and common themes emerged across all interviews? Look for similarities in responses, shared concerns, and recurring topics.

2. DIVERSE PERSPECTIVES: What different viewpoints or unique insights did different personas provide? Highlight contrasting opinions or approaches.

3. PAIN POINTS & OPPORTUNITIES: What challenges, frustrations, or unmet needs were identified? What opportunities for improvement emerged?

4. ACTIONABLE RECOMMENDATIONS: Based on these insights, what specific actions should be taken? Provide concrete, implementable suggestions.

Keep the analysis thorough but well-organized and actionable.

Interview Data:
{interview_summary}
"""

# Node Functions
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
    """Conduct interview with current persona (includes follow-up)"""
    persona = state['personas'][state['current_persona_index']]
    question = state['interview_questions'][state['current_question_index']]
    
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
        "answer": answer,
        "is_followup": False
    }]
    
    # If last main question, add follow-up
    if state['current_question_index'] + 1 >= len(state['interview_questions']):
        
        # Add ONE follow-up (only if not done already)
        if not any(entry.get("is_followup") for entry in history):
            followup_q = ask_ai(
                followup_question_prompt.format(
                    persona_name=persona.name,
                    previous_answer=answer
                )
            )
            
            followup_ans = ask_ai(
                followup_answer_prompt.format(
                    persona_name=persona.name,
                    persona_age=persona.age,
                    persona_job=persona.job,
                    persona_traits=persona.traits,
                    followup_question=followup_q
                )
            )
            
            history.append({
                "question": followup_q,
                "answer": followup_ans,
                "is_followup": True
            })
        
        # Save interview & advance to next persona
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

# Workflow Builder
def build_interview_workflow():
    """Build the complete interview workflow graph"""
    workflow = StateGraph(InterviewState)
    
    # Add all nodes
    workflow.add_node("config", configuration_node)
    workflow.add_node("personas", persona_generation_node)
    workflow.add_node("interview", interview_node)
    workflow.add_node("synthesize", synthesis_node)
    
    # Define connections
    workflow.set_entry_point("config")
    workflow.add_edge("config", "personas")
    workflow.add_edge("personas", "interview")
    
    # Conditional routing
    workflow.add_conditional_edges(
        "interview",
        interview_router,
        {
            "interview": "interview",
            "synthesize": "synthesize"
        }
    )
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()