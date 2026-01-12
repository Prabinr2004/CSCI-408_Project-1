# ReAct Agent

**Live Demo:** https://react-agent-07nd.onrender.com

A ReAct (Reasoning + Acting) AI agent implementation in Python using OpenRouter API. The agent reasons about problems, identifies what actions to take, and uses tools to gather information and solve tasks.

## Overview

This project implements a ReAct agent that follows a loop: the agent reasons about a problem, identifies what tool to use, executes the tool, observes the results, and repeats until it has a final answer. It includes both a CLI and web interface.

## Quick Start

### Setup

```bash
git clone <repo-url>
cd "assignment 2"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Get API Key

1. Sign up at https://openrouter.ai
2. Create `.env` file:
   ```
   OPENROUTER_API_KEY=sk-or-your-key
   ```

### Run

**CLI:**
```bash
python main.py
```

**Web (http://localhost:5001):**
```bash
python app.py
```

## Architecture

The agent follows this pattern:

1. User provides a question
2. Agent sends question + system prompt to LLM
3. LLM responds with reasoning and a tool call
4. Agent parses the tool call and executes it
5. Agent adds the tool result to conversation history
6. Loop back to step 2 until agent returns "Final Answer"

## Available Tools

- `get_weather(location)` - Get current weather
- `search_earthquakes(magnitude)` - Search recent earthquakes
- `search_arxiv(query)` - Search academic papers
- `calculate(expression)` - Evaluate math expressions

## Project Structure

```
.
├── agent.py            # ReAct loop implementation
├── tool_parser.py      # Parse tool calls from LLM responses
├── tools.py            # Tool implementations and registry
├── app.py              # Flask web server
├── main.py             # CLI interface
├── templates/          # Web UI templates
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## Configuration

### Change Model

Edit line 27 in `agent.py`:
```python
model = "openrouter/auto"  # Change to preferred model
```

### Max Iterations

Edit line 31 in `agent.py`:
```python
max_iterations = 20
```

### Add Tool

1. Add function to `tools.py` with `@register_tool` decorator
2. Update system prompt in `agent.py`

Example:
```python
@register_tool
def my_tool(arg: str) -> Dict[str, Any]:
    return {"success": True, "data": result}
```

## Deployment

### Render

1. Push to GitHub
2. Create Web Service at https://render.com
3. Connect your GitHub repo
4. Set environment variable `OPENROUTER_API_KEY`
5. Deploy

### Local with Gunicorn

```bash
gunicorn -w 1 -b 0.0.0.0:5001 app:app
```

## API Usage

POST to `/api/chat`:

```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?"}'
```

## Requirements

- Python 3.8+
- Flask 3.0
- requests

## Troubleshooting

**API key not found:** Create `.env` with `OPENROUTER_API_KEY`

**Port 5001 in use:** Change port in `app.py` or run CLI mode

**Agent loops infinitely:** Check system prompt is clear about stop condition

**Tool not found:** Verify `@register_tool` decorator is present

## License

MIT
