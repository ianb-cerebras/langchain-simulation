# UXR Simulation Architecture

## Overview
This system provides AI-powered user research simulation with two implementation paths:
1. **LangGraph Multi-Agent System** (Primary) - Sophisticated workflow orchestration
2. **Enhanced UXR** (Fallback) - Lightweight, reliable alternative

## Files

### Core Components

#### `UXR.py` (Original)
- Jupyter notebook-style implementation
- Complete LangGraph workflow with visual debugging
- Educational/demonstration purposes
- Interactive execution with progress visualization

#### `uxr_core.py` (Extracted Core)
- Reusable components from UXR.py
- All node functions, state definitions, and prompts
- No Jupyter/IPython dependencies
- Pure LangGraph workflow logic

#### `uxr_api.py` (API Bridge)
- Main integration point for web application
- Handles both LangGraph and fallback modes
- Outputs JSON for dashboard consumption
- Graceful degradation on errors

#### `enhanced_uxr.py` (Fallback)
- Lightweight implementation without LangGraph
- Direct API calls to Cerebras
- Always produces valid output
- Used when LangGraph dependencies unavailable

## Architecture Flow

```
User Request → uxr_api.py
                ├─→ [Try LangGraph]
                │    └─→ uxr_core.py → LangGraph Workflow → JSON
                └─→ [Fallback]
                     └─→ enhanced_uxr.py → Simple Flow → JSON
```

## LangGraph Workflow (uxr_core.py)

```
Configuration Node
    ↓
Persona Generation Node
    ↓
Interview Node (loops for each persona/question)
    ↓
Synthesis Node
    ↓
JSON Output
```

### Nodes:
1. **Configuration**: Generates interview questions based on research topic
2. **Persona Generation**: Creates diverse user personas with structured output
3. **Interview**: Simulates realistic responses with follow-up questions
4. **Synthesis**: Analyzes all interviews for insights and recommendations

## Usage

### Command Line
```bash
# Using uxr_api.py (with automatic fallback)
python3 uxr_api.py "Research question" "Target audience" num_interviews num_questions

# Using enhanced_uxr.py directly
UXR_QUESTION="Your question" UXR_AUDIENCE="Target" python3 enhanced_uxr.py
```

### Python Import
```python
from uxr_api import run_langgraph_research

result = run_langgraph_research(
    question="How do users feel about AI?",
    audience="Tech professionals",
    num_interviews=5,
    num_questions=3
)
```

## Output Format
```json
{
  "keyInsights": "Main finding from research",
  "observations": "Patterns observed",
  "takeaways": "Actionable recommendations",
  "participants": [
    {
      "id": 1,
      "header": "Persona Name",
      "type": "Audience Type",
      "status": "Traits",
      "target": "Age",
      "limit": "Job"
    }
  ],
  "metadata": {
    "workflow": "langgraph|enhanced_uxr",
    "execution_time": "10.5s"
  }
}
```

## Dashboard Integration

The dashboard (`app/dashboard/page.tsx`) fetches results via `/api/uxr-result` endpoint:
- Displays key insights in card components
- Shows participant table with persona details
- Handles both real-time and cached results

## Dependencies

### Required (Core)
- Python 3.9+
- Cerebras API key

### Optional (Full LangGraph)
- langchain
- langchain_cerebras
- langgraph
- pydantic

## Environment Variables
```bash
CEREBRAS_API_KEY=your_api_key_here
UXR_QUESTION="Research question"
UXR_AUDIENCE="Target demographic"
UXR_NUM_INTERVIEWS=5
UXR_NUM_QUESTIONS=3
```

## Testing
Run the test suite:
```bash
python3 test_uxr_integration.py
```

## Key Design Decisions

1. **Preserve Original Logic**: UXR.py logic remains intact in uxr_core.py
2. **Graceful Degradation**: Always produces output, even on errors
3. **Clean Separation**: Each file has single responsibility
4. **Dashboard Compatibility**: Consistent JSON format across implementations
5. **Progress Visibility**: stderr for progress, stdout for JSON output

