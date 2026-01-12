# AI Coding Agent Instructions

## Project Overview

**Capstone CSCI 480 - Assignment 2: ReAct Agent from Scratch**

A complete ReAct-style LLM agent with both CLI and Flask web interfaces. Pure Python with OpenRouter API—no frameworks (LangChain, CrewAI, AutoGen).

**Key Tech:**
- OpenRouter API for LLM calls via `requests` library
- 4 tools: Weather (wttr.in), Earthquakes (USGS), arXiv search, Calculator
- Flask web app (`app.py`) with real-time iteration display
- Manual ReAct loop: Reason → Act → Observe → Loop
- Runs in 2 modes: CLI (`main.py`) or web server (`app.py`)

## Architecture & Code Organization

### Directory Structure
```
assignment 2/
├── agent.py             # Core ReAct loop - LLM calls, message history, iteration control
├── main.py              # CLI interface - terminal mode for interactive/batch queries
├── app.py               # Flask web server - /api/chat endpoint with iteration stream
├── tool_parser.py       # Extract & execute tool calls from LLM output (regex-based)
├── tools.py             # Tool registry (@register_tool decorator) & implementations
├── templates/index.html # Web UI - real-time chat interface
└── requirements.txt     # requests, Flask, gunicorn
```

### Data Flow: The ReAct Loop (agent.py:120–260)

```
USER INPUT
    ↓
[INITIALIZE] System prompt added to messages (teaches LLM format & stop condition)
    ↓
[LOOP ITERATION 1..20]
  1. SEND: messages → OpenRouter API
  2. RECEIVE: LLM response (reasoning text + maybe tool call)
  3. PARSE: Extract tool_name & args via regex (tool_parser.py:40–60)
  4. EXECUTE: Call tool from TOOLS registry, get {success, error/data} dict
  5. APPEND: Add LLM response + tool result to messages
  6. CHECK: Does response contain "Final Answer:"? → exit loop
  7. ITERATE: Return to step 1
    ↓
RETURN final answer or error
```

**Why this matters:** Agent learns iteratively. Each tool result shapes the next reasoning step.

## Critical Implementation Details

### 1. Tool Registration & Execution (tools.py)

```python
@register_tool  # Decorator adds function to TOOLS dict by name
def get_weather(location: str) -> Dict[str, Any]:
    try:
        response = requests.get(f"https://wttr.in/{location}?format=j1")
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Tool call format (what LLM outputs):**
```
Reasoning text here...

Tool: get_weather
Arguments: {"location": "Paris, France"}
```

Parser uses regex (tool_parser.py:40–60) to extract exact format.

### 2. System Prompt (agent.py:84–120)

The prompt teaches:
- **Task:** You're a helpful assistant that answers questions using tools
- **Format:** Exact "Tool: name\nArguments: {json}" format (critical for parsing)
- **Stop condition:** Output "Final Answer:" when done
- **Tool list:** Available tools with parameter descriptions

**Critical:** If prompt is vague, agent loops infinitely or uses wrong tools.

### 3. Error Recovery (tool_parser.py:150–195)

When parsing fails, return error dict and tell agent to retry:
- **Invalid JSON?** Return error, agent tries again with correct syntax
- **Misspelled tool?** Return error listing available tools
- **Missing args?** Return error with expected signature

Agent sees errors in messages and self-corrects.

### 4. Iteration Limits (agent.py:31)

`max_iterations = 20` prevents infinite loops. If agent doesn't say "Final Answer:" after 20 calls, return error.

## Developer Workflows

### Setup (One-time)

```bash
# 1. Get OpenRouter API key from https://openrouter.ai (free tier available)
# 2. Set environment variable
export OPENROUTER_API_KEY="sk-or-..."

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Create .env file in project root
echo "OPENROUTER_API_KEY=sk-or-..." > .env
```

### Running the Agent

**CLI mode (terminal):**
```bash
python main.py                    # Interactive: ask multiple questions
python main.py "What's 2^10?"     # Batch mode: single query, exit
```

**Web mode (Flask server):**
```bash
python app.py                     # Starts on http://localhost:5000
# Browser: http://localhost:5000
# Or POST to http://localhost:5000/api/chat with {"message": "..."}
```

### Testing Individual Components

```bash
python tools.py              # Test all 4 tools independently
python tool_parser.py        # Test parsing valid/invalid tool calls
python agent.py              # Run single agent query
```

### Debugging Checklist

| Problem | Solution |
|---------|----------|
| Agent loops infinitely | Check system prompt (agent.py:84–120); maybe stop condition is unclear |
| Tool not found error | Verify `@register_tool` decorator used; tool name matches exactly |
| Tool always fails | Run `python tools.py` to test API connectivity first |
| Invalid JSON parsing | Review LLM output vs regex in tool_parser.py:40–60 |
| API key rejected | Run `echo $OPENROUTER_API_KEY`; check .env file exists |
| Web app 500 error | Check Flask `/api/chat` endpoint (app.py:78); ensure agent.create_agent() works |

## Integration Points & External APIs

| API | Purpose | Auth | Free? |
|-----|---------|------|-------|
| OpenRouter | LLM gateway (auto picks free models) | API key | Yes |
| wttr.in | Weather data | None | Yes |
| USGS | Earthquake data | None | Yes |
| arXiv | Academic papers | None | Yes |

All HTTP calls use `requests` library. Tools return structured dicts; agent interprets results.

## Project-Specific Patterns

**Tool pattern:** `@register_tool` decorator, returns `{"success": bool, "error"?/"data"?}`

**Message structure:** System prompt first, then alternating user/assistant, tool results as user messages

**Tool format:** `Tool: <name>\nArguments: {...}` (regex-parseable)

**Error handling:** Tools return error dicts; agent messages include feedback; agent learns from errors

**Naming:** `snake_case` functions, `TOOLS` registry dict, `ToolCall` dataclass

## Key Files Reference

- **[agent.py](agent.py#L84)** — System prompt (makes or breaks agent)
- **[agent.py](agent.py#L120)** — Main ReAct loop implementation
- **[tool_parser.py](tool_parser.py#L40)** — Regex patterns for tool extraction
- **[tools.py](tools.py#L18)** — Tool registration & HTTP implementations
- **[main.py](main.py#L60)** — CLI argument parsing
- **[app.py](app.py#L78)** — Flask `/api/chat` endpoint

## Quick Edits

- **Change LLM model:** `agent.py` line 27 (default: `"openrouter/auto"`)
- **Change max iterations:** `agent.py` line 31 (default: `20`)
- **Add new tool:** Create function in `tools.py`, decorate with `@register_tool`, update system prompt in `agent.py`
- **Change web UI:** Edit `templates/index.html`
- **Change Flask routes:** Edit `app.py`

---

*Last updated: January 2026. Covers both CLI (`main.py`) and Flask modes (`app.py`).*
