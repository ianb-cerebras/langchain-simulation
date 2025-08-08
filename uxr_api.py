#!/usr/bin/env python3
"""
API bridge for UXR LangGraph workflow.
Converts LangGraph workflow output to JSON for dashboard consumption.
"""

import json
import os
import sys
import time
from typing import Dict, List, Any

try:
    from uxr_core import (
        build_interview_workflow,
        InterviewState,
        DEFAULT_NUM_INTERVIEWS,
        DEFAULT_NUM_QUESTIONS
    )
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ LangGraph not available, falling back to enhanced_uxr: {e}", file=sys.stderr)
    LANGGRAPH_AVAILABLE = False
    DEFAULT_NUM_INTERVIEWS = 10
    DEFAULT_NUM_QUESTIONS = 5

def format_persona_for_dashboard(persona, index: int, audience: str) -> Dict:
    """Convert persona object to dashboard table format"""
    if hasattr(persona, '__dict__'):
        # Pydantic model
        return {
            "id": index + 1,
            "header": persona.name,
            "type": audience,
            "status": ', '.join(persona.traits[:2]) if persona.traits else "Unknown",
            "target": str(persona.age),
            "limit": persona.job
        }
    else:
        # Dict format (fallback)
        return {
            "id": index + 1,
            "header": persona.get('name', f'Participant {index + 1}'),
            "type": audience,
            "status": ', '.join(persona.get('traits', ['Unknown'])[:2]),
            "target": str(persona.get('age', 25)),
            "limit": persona.get('job', 'Unknown')
        }

def extract_insights_from_synthesis(synthesis_text: str, research_question: str) -> Dict[str, str]:
    """Extract structured insights from synthesis text"""
    insights = {
        "keyInsights": "",
        "observations": "",
        "takeaways": ""
    }
    
    if not synthesis_text:
        return {
            "keyInsights": f"Analysis completed for: {research_question}",
            "observations": "Multiple perspectives gathered from diverse participants",
            "takeaways": "Further analysis recommended based on initial findings"
        }
    
    # Parse synthesis sections
    lines = synthesis_text.split('\n')
    current_section = None
    section_content = []
    
    for line in lines:
        line = line.strip()
        if 'KEY THEMES' in line.upper() or 'THEMES' in line.upper():
            if current_section and section_content:
                insights[current_section] = ' '.join(section_content[:2])  # First 2 sentences
            current_section = 'keyInsights'
            section_content = []
        elif 'DIVERSE PERSPECTIVES' in line.upper() or 'PERSPECTIVES' in line.upper():
            if current_section and section_content:
                insights[current_section] = ' '.join(section_content[:2])
            current_section = 'observations'
            section_content = []
        elif 'ACTIONABLE RECOMMENDATIONS' in line.upper() or 'RECOMMENDATIONS' in line.upper():
            if current_section and section_content:
                insights[current_section] = ' '.join(section_content[:2])
            current_section = 'takeaways'
            section_content = []
        elif line and current_section:
            # Split by sentence and add to content
            sentences = line.split('. ')
            section_content.extend([s.strip() for s in sentences if s.strip()])
    
    # Capture last section
    if current_section and section_content:
        insights[current_section] = '. '.join(section_content[:2]) + '.'
    
    # Ensure all fields have content
    if not insights["keyInsights"]:
        insights["keyInsights"] = synthesis_text.split('.')[0] + '.' if synthesis_text else f"Research completed on {research_question}"
    if not insights["observations"]:
        insights["observations"] = "Participants showed varied perspectives based on their backgrounds and experiences."
    if not insights["takeaways"]:
        insights["takeaways"] = "Consider implementing changes based on user feedback and identified patterns."
    
    return insights

def run_langgraph_research(question: str, audience: str, num_interviews: int = None, num_questions: int = None) -> Dict:
    """Execute LangGraph workflow and return formatted results"""
    
    if not LANGGRAPH_AVAILABLE:
        # Fall back to enhanced_uxr
        print("⚠️ Using enhanced_uxr fallback", file=sys.stderr)
        os.environ["UXR_QUESTION"] = question
        os.environ["UXR_AUDIENCE"] = audience
        os.environ["UXR_NUM_INTERVIEWS"] = str(num_interviews or 3)
        
        # Import and run enhanced_uxr
        from enhanced_uxr import main as enhanced_main
        from io import StringIO
        import contextlib
        
        f = StringIO()
        with contextlib.redirect_stdout(f):
            enhanced_main()
        output = f.getvalue()
        
        try:
            # Parse JSON from output - enhanced_uxr outputs pretty-printed JSON
            # Find the JSON content (starts with { and ends with })
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = output[json_start:json_end]
                return json.loads(json_str)
            else:
                # Try parsing entire output
                return json.loads(output)
        except Exception as parse_error:
            print(f"⚠️ Failed to parse enhanced_uxr output: {parse_error}", file=sys.stderr)
            print(f"Output was: {output[:500]}", file=sys.stderr)
            return {
                "keyInsights": f"Fallback analysis for: {question}",
                "observations": "Limited analysis available",
                "takeaways": "Consider running full analysis",
                "participants": []
            }
    
    print(f"🚀 Starting LangGraph research workflow...", file=sys.stderr)
    
    # Build workflow
    workflow = build_interview_workflow()
    
    # Initialize state
    initial_state = {
        "research_question": question,
        "target_demographic": audience,
        "num_interviews": num_interviews or DEFAULT_NUM_INTERVIEWS,
        "num_questions": num_questions or DEFAULT_NUM_QUESTIONS,
        "interview_questions": [],
        "personas": [],
        "current_persona_index": 0,
        "current_question_index": 0,
        "current_interview_history": [],
        "all_interviews": [],
        "synthesis": ""
    }
    
    try:
        start_time = time.time()
        
        # Execute workflow with progress updates
        print(f"🔧 Configuring research: {question}", file=sys.stderr)
        print(f"📊 Planning {initial_state['num_interviews']} interviews with {initial_state['num_questions']} questions each", file=sys.stderr)
        
        # Run the workflow
        final_state = workflow.invoke(initial_state, {"recursion_limit": 100})
        
        total_time = time.time() - start_time
        print(f"✅ Workflow complete! {len(final_state['all_interviews'])} interviews in {total_time:.1f}s", file=sys.stderr)
        
        # Extract insights from synthesis
        insights = extract_insights_from_synthesis(
            final_state.get('synthesis', ''),
            question
        )
        
        # Format participants for dashboard
        participants = []
        for i, interview in enumerate(final_state.get('all_interviews', [])):
            persona = interview.get('persona')
            if persona:
                participants.append(format_persona_for_dashboard(persona, i, audience))
        
        # If no participants were generated, use personas directly
        if not participants and final_state.get('personas'):
            for i, persona in enumerate(final_state['personas']):
                participants.append(format_persona_for_dashboard(persona, i, audience))
        
        # Combine results
        result = {
            **insights,
            "participants": participants,
            "metadata": {
                "research_question": question,
                "target_demographic": audience,
                "num_interviews": len(final_state.get('all_interviews', [])),
                "num_questions": len(final_state.get('interview_questions', [])),
                "execution_time": f"{total_time:.1f}s",
                "workflow": "langgraph"
            }
        }
        
        # Include full synthesis for detailed view
        if final_state.get('synthesis'):
            result["full_synthesis"] = final_state['synthesis']
        
        # Include sample responses for detail view
        if final_state.get('all_interviews'):
            sample_responses = []
            for interview in final_state['all_interviews'][:3]:  # First 3 interviews
                persona = interview.get('persona')
                responses = interview.get('responses', [])
                if responses:
                    sample_responses.append({
                        "persona_name": persona.name if hasattr(persona, 'name') else persona.get('name', 'Unknown'),
                        "sample_answer": responses[0].get('answer', '') if responses else ''
                    })
            result["sample_responses"] = sample_responses
        
        return result
        
    except Exception as e:
        print(f"❌ Error during LangGraph execution: {e}", file=sys.stderr)
        
        # Fall back to enhanced_uxr on error
        print("⚠️ Falling back to enhanced_uxr due to error", file=sys.stderr)
        os.environ["UXR_QUESTION"] = question
        os.environ["UXR_AUDIENCE"] = audience
        os.environ["UXR_NUM_INTERVIEWS"] = str(num_interviews or 3)
        
        try:
            from enhanced_uxr import main as enhanced_main
            from io import StringIO
            import contextlib
            
            f = StringIO()
            with contextlib.redirect_stdout(f):
                enhanced_main()
            output = f.getvalue()
            
            # Parse JSON from output
            lines = output.strip().split('\n')
            for line in reversed(lines):
                if line.strip().startswith('{'):
                    result = json.loads(line)
                    result["metadata"] = {
                        "workflow": "enhanced_uxr_fallback",
                        "error": str(e)
                    }
                    return result
        except Exception as fallback_error:
            print(f"⚠️ Fallback also failed: {fallback_error}", file=sys.stderr)
            return {
                "keyInsights": f"Error analyzing: {question}",
                "observations": f"An error occurred: {str(e)}",
                "takeaways": "Please try again or check system configuration",
                "participants": [],
                "metadata": {
                    "workflow": "error",
                    "error": str(e)
                }
            }

def main():
    """Main entry point for CLI usage"""
    # Get inputs from environment variables or arguments
    question = os.getenv("UXR_QUESTION", "How do users feel about AI assistants?")
    audience = os.getenv("UXR_AUDIENCE", "Technology professionals aged 25-45")
    num_interviews = int(os.getenv("UXR_NUM_INTERVIEWS", "5"))
    num_questions = int(os.getenv("UXR_NUM_QUESTIONS", "3"))
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        question = sys.argv[1]
    if len(sys.argv) > 2:
        audience = sys.argv[2]
    if len(sys.argv) > 3:
        num_interviews = int(sys.argv[3])
    if len(sys.argv) > 4:
        num_questions = int(sys.argv[4])
    
    # Run research
    result = run_langgraph_research(question, audience, num_interviews, num_questions)
    
    # Output JSON result
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()