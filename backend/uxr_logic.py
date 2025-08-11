# -*- coding: utf-8 -*-
"""Minimal port of UXR.py logic into a callable function.
Preserves node logic and processing; removes interactive input and display."""

import os
import time
from datetime import datetime
from typing import Dict, List, TypedDict, Optional

from pydantic import BaseModel, Field, ValidationError

from langchain_cerebras import ChatCerebras
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI  # Imported to keep parity with UXR.py
from langgraph.graph import StateGraph, END


# Configuration Constants (kept from UXR.py)
DEFAULT_NUM_INTERVIEWS = 10
DEFAULT_NUM_QUESTIONS = 5


# LLM setup (kept from UXR.py; requires CEREBRAS_API_KEY env var)
system_prompt = (
    "You are a helpful assistant. Provide a direct, clear response without showing your "
    "thinking process. Respond directly without using <think> tags or showing internal reasoning."
)

llm = ChatCerebras(model="llama3.3-70b", temperature=0.7, max_tokens=800)


def _init_llm(api_key: Optional[str]) -> None:
    """Reinitialize global LLM with a provided API key if given.
    Keeps logic identical; only source of credentials changes per request."""
    global llm
    if api_key:
        # Prefer explicit api_key if supported; otherwise set env var
        try:
            llm = ChatCerebras(
                model="llama3.3-70b",
                temperature=0.7,
                max_tokens=800,
                api_key=api_key,  # type: ignore[arg-type]
            )
            return
        except TypeError:
            # Fallback: use env variable if api_key param unsupported
            os.environ["CEREBRAS_API_KEY"] = api_key
            llm = ChatCerebras(model="llama3.3-70b", temperature=0.7, max_tokens=800)
            return


def ask_ai(prompt: str) -> str:
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ])
    return response.content


# ----- State and models (kept from UXR.py) -----
class Persona(BaseModel):
    name: str = Field(..., description="Full name of the persona")
    age: int = Field(..., description="Age in years")
    job: str = Field(..., description="Job title or role")
    traits: List[str] = Field(..., description="3-4 personality traits")
    communication_style: str = Field(..., description="How this person communicates")


class PersonasList(BaseModel):
    personas: List[Persona] = Field(..., description="List of generated personas")


class InterviewState(TypedDict):
    research_question: str
    target_demographic: str
    num_interviews: int
    num_questions: int
    interview_questions: List[str]
    personas: List[Persona]
    current_persona_index: int
    current_question_index: int
    current_interview_history: List[Dict]
    interview_start_time: float
    all_interviews: List[Dict]
    synthesis: str


# ----- Node prompts (kept from UXR.py) -----
class Questions(BaseModel):
    questions: List = Field(..., description="List of interview questions")


question_gen_prompt = (
    """Generate exactly {DEFAULT_NUM_QUESTIONS} interview questions about: {research_question}. """
    """Use the provided structured output to format the questions."""
)


def configuration_node(state: InterviewState) -> Dict:
    print(f"\n🔧 Configuring research: {state['research_question']}")
    print(
        f"📊 Planning {DEFAULT_NUM_INTERVIEWS} interviews with {DEFAULT_NUM_QUESTIONS} questions each"
    )

    structured_llm = llm.with_structured_output(Questions)
    questions = structured_llm.invoke(
        question_gen_prompt.format(
            DEFAULT_NUM_QUESTIONS=DEFAULT_NUM_QUESTIONS,
            research_question=state["research_question"],
        )
    )
    questions = questions.questions
    print(f"✅ Generated {len(questions)} questions")

    return {
        "num_questions": DEFAULT_NUM_QUESTIONS,
        "num_interviews": DEFAULT_NUM_INTERVIEWS,
        "interview_questions": questions,
    }


persona_prompt = (
    "Generate exactly {num_personas} unique personas for an interview. "
    "Each should belong to the target demographic: {demographic}. "
    "Respond only in JSON using this format: { personas: [ ... ] }"
)


def persona_generation_node(state: InterviewState) -> Dict:
    num_personas = state["num_interviews"]
    demographic = state["target_demographic"]
    max_retries = 5

    print(f"\n👥 Creating {state['num_interviews']} personas...")
    print(persona_prompt.format(num_personas=num_personas, demographic=demographic))

    structured_llm = llm.with_structured_output(PersonasList)

    raw_output = None
    for attempt in range(max_retries):
        try:
            raw_output = structured_llm.invoke(
                [
                    {
                        "role": "user",
                        "content": persona_prompt.format(
                            num_personas=num_personas, demographic=demographic
                        ),
                    }
                ]
            )
            if raw_output is None:
                raise ValueError("LLM returned None")

            validated = PersonasList.model_validate(raw_output)

            if len(validated.personas) != num_personas:
                raise ValueError(
                    f"Expected {num_personas} personas, got {len(validated.personas)}"
                )

            personas = validated.personas
            for i, p in enumerate(personas):
                print(f"Persona {i+1}: {p}")

            return {
                "personas": personas,
                "current_persona_index": 0,
                "current_question_index": 0,
                "all_interviews": [],
            }

        except (ValidationError, ValueError, TypeError) as e:
            print(f"❌ Attempt {attempt+1} failed: {e}")
            print(raw_output)
            if attempt == max_retries - 1:
                raise RuntimeError(f"❗️Failed after {max_retries} attempts")


interview_prompt = (
    """You are {persona_name}, a {persona_age}-year-old {persona_job} who is {persona_traits}.
Answer the following question in 2-3 sentences:

Question: {question}

Answer as {persona_name} in your own authentic voice. Be brief but creative and unique, and make each answer conversational.
BE REALISTIC – do not be overly optimistic. Mimic real human behavior based on your persona, and give honest answers."""
)


def interview_node(state: InterviewState) -> Dict:
    persona = state["personas"][state["current_persona_index"]]
    question = state["interview_questions"][state["current_question_index"]]

    print(
        f"\n💬 Interview {state['current_persona_index'] + 1}/{len(state['personas'])} - {persona.name}"
    )
    print(f"Q{state['current_question_index'] + 1}: {question}")

    prompt = interview_prompt.format(
        persona_name=persona.name,
        persona_age=persona.age,
        persona_job=persona.job,
        persona_traits=persona.traits,
        question=question,
    )
    answer = ask_ai(prompt)
    print(f"A: {answer}")

    history = state.get("current_interview_history", []) + [
        {
            "question": question,
            "answer": answer,
        }
    ]

    if state["current_question_index"] + 1 >= len(state["interview_questions"]):
        return {
            "all_interviews": state["all_interviews"]
            + [{"persona": persona, "responses": history}],
            "current_interview_history": [],
            "current_question_index": 0,
            "current_persona_index": state["current_persona_index"] + 1,
        }

    return {
        "current_interview_history": history,
        "current_question_index": state["current_question_index"] + 1,
    }


synthesis_prompt_template = (
    """Analyze these {num_interviews} user interviews about "{research_question}" among {target_demographic} and concise yet comprehensive analysis:

1. KEY THEMES: What patterns and common themes emerged across all interviews? Look for similarities in responses, shared concerns, and recurring topics.

2. DIVERSE PERSPECTIVES: What different viewpoints or unique insights did different personas provide? Highlight contrasting opinions or approaches.

3. PAIN POINTS & OPPORTUNITIES: What challenges, frustrations, or unmet needs were identified? What opportunities for improvement emerged?

4. ACTIONABLE RECOMMENDATIONS: Based on these insights, what specific actions should be taken? Provide concrete, implementable suggestions.

Keep the analysis thorough but well-organized and actionable.

Interview Data:
{interview_summary}
"""
)


def synthesis_node(state: InterviewState) -> Dict:
    print("\n🧠 Analyzing all interviews...")

    interview_summary = f"Research Question: {state['research_question']}\n"
    interview_summary += f"Target Demographic: {state['target_demographic']}\n"
    interview_summary += f"Number of Interviews: {len(state['all_interviews'])}\n\n"

    for i, interview in enumerate(state["all_interviews"], 1):
        p = interview["persona"]
        interview_summary += f"Interview {i} - {p.name} ({p.age}, {p.job}):\n"
        interview_summary += f"Persona Traits: {p.traits}\n"
        for j, qa in enumerate(interview["responses"], 1):
            interview_summary += f"Q{j}: {qa['question']}\n"
            interview_summary += f"A{j}: {qa['answer']}\n"
        interview_summary += "\n"

    prompt = synthesis_prompt_template.format(
        num_interviews=len(state["all_interviews"]),
        research_question=state["research_question"],
        target_demographic=state["target_demographic"],
        interview_summary=interview_summary,
    )

    try:
        synthesis = ask_ai(prompt)
    except Exception as e:
        synthesis = f"Error during synthesis: {e}\n\nRaw interview data available for manual analysis."

    print("\n" + "=" * 60)
    print("🎯 COMPREHENSIVE RESEARCH INSIGHTS")
    print("=" * 60)
    print(f"Research Topic: {state['research_question']}")
    print(f"Demographic: {state['target_demographic']}")
    print(f"Interviews Conducted: {len(state['all_interviews'])}")
    print("-" * 60)
    print(synthesis)
    print("=" * 60)

    return {"synthesis": synthesis}


def interview_router(state: InterviewState) -> str:
    if state["current_persona_index"] >= len(state["personas"]):
        return "synthesize"
    else:
        return "interview"


def build_interview_workflow():
    workflow = StateGraph(InterviewState)

    workflow.add_node("config", configuration_node)
    workflow.add_node("personas", persona_generation_node)
    workflow.add_node("interview", interview_node)
    workflow.add_node("synthesize", synthesis_node)

    workflow.set_entry_point("config")
    workflow.add_edge("config", "personas")
    workflow.add_edge("personas", "interview")
    workflow.add_conditional_edges(
        "interview",
        interview_router,
        {"interview": "interview", "synthesize": "synthesize"},
    )
    workflow.add_edge("synthesize", END)

    return workflow.compile()


def serialize_state(state: Dict) -> Dict:
    """Convert final state to a clean JSON-serializable payload, preserving original content."""
    return {
        "research_question": state.get("research_question", ""),
        "target_demographic": state.get("target_demographic", ""),
        "timestamp": datetime.now().isoformat(),
        "num_interviews": state.get("num_interviews", 0),
        "num_questions": state.get("num_questions", 0),
        "interview_questions": state.get("interview_questions", []),
        "personas": [
            p.model_dump() if hasattr(p, "model_dump") else p
            for p in state.get("personas", [])
        ],
        "all_interviews": [
            {
                "persona": interview["persona"].model_dump()
                if hasattr(interview["persona"], "model_dump")
                else interview["persona"],
                "responses": interview["responses"],
            }
            for interview in state.get("all_interviews", [])
        ],
        "synthesis": state.get("synthesis", ""),
    }


def execute_research(
    research_question: str,
    target_demographic: str,
    num_interviews: int,
    num_questions: int,
    cerebras_api_key: Optional[str] = None,
) -> Dict:
    """Run the complete LangGraph workflow with provided inputs and return serialized results."""
    _init_llm(cerebras_api_key)
    workflow = build_interview_workflow()

    start_time = time.time()
    initial_state: InterviewState = {
        "research_question": research_question,
        "target_demographic": target_demographic,
        "num_interviews": num_interviews or DEFAULT_NUM_INTERVIEWS,
        "num_questions": num_questions or DEFAULT_NUM_QUESTIONS,
        "interview_questions": [],
        "personas": [],
        "current_persona_index": 0,
        "current_question_index": 0,
        "current_interview_history": [],
        "all_interviews": [],
        "synthesis": "",
        "interview_start_time": start_time,
    }

    final_state = workflow.invoke(initial_state, {"recursion_limit": 100})
    return serialize_state(final_state)


