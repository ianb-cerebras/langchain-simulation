# -*- coding: utf-8 -*-
"""Minimal port of UXR.py logic into a callable function.
Preserves node logic and processing; removes interactive input and display."""

import os
import time
from datetime import datetime
from typing import Dict, List, TypedDict, Optional

from pydantic import BaseModel, Field, ValidationError
import json

from langchain_cerebras import ChatCerebras
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI  # Imported to keep parity with UXR.py
from langgraph.graph import StateGraph, END


# Configuration Constants (kept from UXR.py)
DEFAULT_NUM_INTERVIEWS = 11
DEFAULT_NUM_QUESTIONS = 3


# LLM setup (kept from UXR.py; requires CEREBRAS_API_KEY env var)
system_prompt = (
    "You are a helpful assistant. Provide a direct, clear response without showing your "
    "thinking process. Respond directly without using <think> tags or showing internal reasoning."
)

llm: Optional[ChatCerebras] = None
DEBUG: bool = str(os.getenv("UXR_DEBUG", "0")).lower() not in {"", "0", "false", "no"}


def debug_log(*args) -> None:
    if DEBUG:
        try:
            print("[UXR_DEBUG]", *args)
        except Exception:
            pass


def _init_llm(api_key: Optional[str]) -> None:
    """Reinitialize global LLM with a provided API key if given.
    Keeps logic identical; only source of credentials changes per request."""
    global llm
    if api_key:
        # Some backends expect OPENAI_API_KEY; set both to be safe
        os.environ["CEREBRAS_API_KEY"] = api_key
        os.environ["OPENAI_API_KEY"] = api_key
        try:
            llm = ChatCerebras(
                model="llama3.3-70b",
                temperature=0.7,
                max_tokens=800,
                api_key=api_key,  # type: ignore[arg-type]
            )
        except TypeError:
            llm = ChatCerebras(model="llama3.3-70b", temperature=0.7, max_tokens=800)
        debug_log("Initialized LLM", {
            "model": "llama3.3-70b",
            "temperature": 0.7,
            "max_tokens": 800,
            "api_key_present": bool(api_key),
        })
    else:
        # No key provided; leave uninitialized to avoid import-time failures
        llm = None
        debug_log("LLM initialization skipped; no API key provided")


def ask_ai(prompt: str) -> str:
    if llm is None:
        raise RuntimeError("LLM not initialized: missing API key")
    debug_log("ask_ai prompt length", len(prompt))
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ])
    try:
        debug_log("ask_ai response type", type(response).__name__)
    except Exception:
        pass
    return response.content


# ----- State and models (kept from UXR.py) -----
class Persona(BaseModel):
    name: str = Field(..., description="Full name of the persona")
    age: int = Field(..., description="Age in years")
    job: str = Field(..., description="Job title or role")
    traits: List[str] = Field(..., description="3-4 personality traits")
    communication_style: str = Field(..., description="How this person communicates")
    background: str = Field(..., description="One background detail shaping their perspective")


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
    timeline: List[Dict]
    start_time_iso: str


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

    timeline = list(state.get("timeline", []))
    try:
        timeline.append({
            "type": "questions_generated",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "count": len(questions),
        })
    except Exception:
        pass

    return {
        "num_questions": DEFAULT_NUM_QUESTIONS,
        "num_interviews": DEFAULT_NUM_INTERVIEWS,
        "interview_questions": questions,
        "timeline": timeline,
    }


persona_prompt = (
    "Generate exactly {num_personas} unique personas for an interview. "
    "Each should belong to the target demographic: {demographic}. "
    "Respond only in JSON using this exact format: {{\"personas\": [ ... ] }}"
)


def persona_generation_node(state: InterviewState) -> Dict:
    num_personas = state["num_interviews"]
    demographic = state["target_demographic"]
    max_retries = 5

    print(f"\n👥 Creating {state['num_interviews']} personas...")
    print(persona_prompt.format(num_personas=num_personas, demographic=demographic))
    debug_log("persona_generation_node state", {
        "num_personas": num_personas,
        "demographic": demographic,
    })

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
            try:
                preview = raw_output if isinstance(raw_output, str) else getattr(raw_output, "content", str(raw_output))
                preview_str = preview if isinstance(preview, str) else str(preview)
                debug_log(f"raw_output attempt {attempt+1}", preview_str[:500])
                debug_log("raw_output type", type(raw_output).__name__)
            except Exception:
                pass

            # Normalize possible formatting issues from the model
            normalized_output = raw_output

            # 1) If we got a Pydantic model instance back, convert to a dict
            try:
                if hasattr(normalized_output, "model_dump") and callable(normalized_output.model_dump):
                    normalized_output = normalized_output.model_dump()
                    debug_log("normalized via model_dump; keys", list(normalized_output.keys()) if isinstance(normalized_output, dict) else type(normalized_output).__name__)
            except Exception:
                # Best-effort; continue with other normalizations
                pass

            # 2) If we got a LangChain message or object with a string 'content', try JSON-parsing that
            if not isinstance(normalized_output, (dict, list, str)) and hasattr(normalized_output, "content"):
                content = getattr(normalized_output, "content")
                if isinstance(content, str):
                    try:
                        normalized_output = json.loads(content)
                        debug_log("normalized from message.content JSON; keys", list(normalized_output.keys()) if isinstance(normalized_output, dict) else type(normalized_output).__name__)
                    except Exception:
                        # If it's not valid JSON, leave as-is and let validation fail gracefully
                        pass

            # 3) If model returned JSON string, parse it
            if isinstance(normalized_output, str):
                try:
                    normalized_output = json.loads(normalized_output)
                    debug_log("normalized from raw JSON string; keys", list(normalized_output.keys()) if isinstance(normalized_output, dict) else type(normalized_output).__name__)
                except Exception:
                    # Not JSON; keep as-is, validation will handle
                    pass

            # 4) If dict-like, strip whitespace and normalize key casing
            if isinstance(normalized_output, dict):
                # Strip spaces around keys
                normalized_keys = {str(k).strip(): v for k, v in normalized_output.items()}
                # Handle capitalization or stray quotes variations (e.g., '"personas"')
                cleaned_key_map = {}
                for k in list(normalized_keys.keys()):
                    cleaned = str(k).strip().strip("\"'")
                    if cleaned != k:
                        normalized_keys[cleaned] = normalized_keys.pop(k)
                    cleaned_key_map[cleaned.lower()] = cleaned

                # Ensure we have the exact 'personas' key if a variant exists
                if "personas" not in normalized_keys and "personas" in cleaned_key_map:
                    original_key = cleaned_key_map["personas"]
                    normalized_keys["personas"] = normalized_keys.pop(original_key)

                normalized_output = normalized_keys
                debug_log("post-clean keys", list(normalized_keys.keys()))

            # Explicit pre-validation check for clearer error
            if isinstance(normalized_output, dict) and "personas" not in normalized_output:
                debug_log("missing personas key after normalization; keys", list(normalized_output.keys()))
                raise KeyError("personas")

            validated = PersonasList.model_validate(normalized_output)

            if len(validated.personas) != num_personas:
                raise ValueError(
                    f"Expected {num_personas} personas, got {len(validated.personas)}"
                )

            personas = validated.personas
            for i, p in enumerate(personas):
                print(f"Persona {i+1}: {p}")

            timeline = list(state.get("timeline", []))
            try:
                timeline.append({
                    "type": "personas_generated",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "count": len(personas),
                })
            except Exception:
                pass

            return {
                "personas": personas,
                "current_persona_index": 0,
                "current_question_index": 0,
                "all_interviews": [],
                "timeline": timeline,
            }

        except (ValidationError, ValueError, TypeError, KeyError) as e:
            print(f"❌ Attempt {attempt+1} failed: {e}")
            # Log raw output for diagnostics; avoid crashing on repr issues
            try:
                print(raw_output)
            except Exception:
                pass
            try:
                debug_log("normalized_output on failure", normalized_output if isinstance(normalized_output, dict) else type(normalized_output).__name__)
            except Exception:
                pass
            if attempt == max_retries - 1:
                # Raise a clearer error to the API caller
                raise RuntimeError(
                    "Failed to generate personas in valid format after multiple attempts. "
                    "Please try again or adjust the prompt."
                )


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

    # Append timeline event for each answer
    timeline = list(state.get("timeline", []))
    try:
        timeline.append({
            "type": "answer",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "persona_index": state["current_persona_index"],
            "question_index": state["current_question_index"],
        })
    except Exception:
        pass

    if state["current_question_index"] + 1 >= len(state["interview_questions"]):
        # Interview complete for this persona
        try:
            timeline.append({
                "type": "interview_completed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "persona_index": state["current_persona_index"],
            })
        except Exception:
            pass
        return {
            "all_interviews": state["all_interviews"]
            + [{"persona": persona, "responses": history}],
            "current_interview_history": [],
            "current_question_index": 0,
            "current_persona_index": state["current_persona_index"] + 1,
            "timeline": timeline,
        }

    return {
        "current_interview_history": history,
        "current_question_index": state["current_question_index"] + 1,
        "timeline": timeline,
    }


synthesis_prompt_template = (
    """Analyze these {num_interviews} user interviews about "{research_question}" among {target_demographic} and concise yet comprehensive analysis. Keep each section to 3 sentences each:

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

    timeline = list(state.get("timeline", []))
    try:
        timeline.append({
            "type": "synthesis_generated",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
    except Exception:
        pass
    return {"synthesis": synthesis, "timeline": timeline}


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
    start_iso = state.get("start_time_iso") or datetime.utcnow().isoformat() + "Z"
    end_iso = datetime.utcnow().isoformat() + "Z"
    duration_seconds = None
    try:
        if state.get("interview_start_time"):
            duration_seconds = max(0.0, time.time() - float(state["interview_start_time"]))
    except Exception:
        duration_seconds = None

    return {
        "research_question": state.get("research_question", ""),
        "target_demographic": state.get("target_demographic", ""),
        "timestamp": datetime.now().isoformat(),
        "start_time": start_iso,
        "end_time": end_iso,
        "duration_seconds": duration_seconds,
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
        "timeline": state.get("timeline", []),
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
        "timeline": [],
        "start_time_iso": datetime.utcfromtimestamp(start_time).isoformat() + "Z",
    }

    final_state = workflow.invoke(initial_state, {"recursion_limit": 100})
    return serialize_state(final_state)


