"""
REACT AGENT CORE - The main ReAct agent loop

This is where the magic happens. The ReAct (Reasoning + Acting) loop is:

    1. SEND: Send messages + system prompt to LLM
    2. RECEIVE: Get LLM response (includes reasoning and maybe a tool call)
    3. PARSE: Extract tool name and arguments
    4. ACT: Execute the tool (make HTTP request, compute, etc.)
    5. OBSERVE: Get tool result back
    6. APPEND: Add tool call and result to messages
    7. LOOP: Go back to SEND until agent says it's done

WHY THIS LOOP WORKS:
- The agent can reason about what to do ("I need to check weather first")
- The agent decides to take actions (call tools)
- The agent sees the results and can decide what to do next
- This is more powerful than a simple prompt-response because:
  * Agent can use multiple tools in sequence
  * Agent can reason differently based on tool results
  * Agent gradually gathers information to solve complex problems

KEY INSIGHT:
The system prompt teaches the LLM HOW to use tools and WHEN to stop.
If the prompt is bad, the agent will behave badly (infinite loops, wrong tools, etc.)
"""

import requests
import json
from typing import List, Dict, Any, Optional
from tool_parser import parse_and_execute_tool


class ReActAgent:
    """
    A ReAct agent that uses OpenRouter API.
    
    The agent maintains a messages list (conversation history) and:
    1. Sends it to OpenRouter
    2. Parses the response for tool calls
    3. Executes tools
    4. Appends results to messages
    5. Repeats until done
    """
    
    def __init__(self, api_key: str, model: str = "openrouter/auto"):
        """
        Initialize the ReAct agent.
        
        Args:
            api_key: OpenRouter API key
            model: Model to use (default: "openrouter/auto" which picks the best free model)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # This will be populated by run_agent()
        self.messages: List[Dict[str, str]] = []
        self.max_iterations = 20  # Safeguard against infinite loops
        self.iteration_count = 0
    
    def get_system_prompt(self) -> str:
        """
        Generate the system prompt that teaches the agent how to behave.
        
        WHY THIS PROMPT IS WRITTEN THIS WAY:
        
        1. TASK DEFINITION: Clear description of what we're asking for
           - Tells agent its role and goals
        
        2. TOOL INSTRUCTIONS: Exact format for tool calls
           - If format is vague, agent will output garbage
           - We use "Tool: <name>\nArguments: <json>" format
           - This is regex-parseable and LLMs are good at following formats
        
        3. STOPPING CONDITION: When to output final answer
           - If we don't tell agent to stop, it loops forever
           - "Final Answer:" is the stop signal
        
        4. REASONING REQUIREMENT: Always show thinking
           - Helps us debug what agent was thinking
           - Improves agent behavior (chain of thought)
        
        5. FAILURE HANDLING: What to do if tool fails
           - Agent should recover and try something else
           - Don't just repeat the same failed tool
        
        6. CONSTRAINTS: Safeguards
           - Max iterations (to prevent infinite loops)
           - Available tools list
        """
        
        from tools import get_tools_description
        
        return f"""You are a helpful AI assistant with access to tools.

Your job is to answer the user's question accurately using available tools.

IMPORTANT - You MUST follow this format EXACTLY:

To use a tool, format your response like this:
- First, explain your reasoning
- Then use a tool:

Tool: <tool_name>
Arguments: {{"arg1": "value1", "arg2": "value2"}}

After you use a tool, I will give you the result. Then you can:
1. Use another tool if needed
2. Provide the Final Answer

When you have enough information to answer, output:

Final Answer: <your answer>

{get_tools_description()}

IMPORTANT CONSTRAINTS:
- Always show your reasoning before using a tool
- If a tool fails, try a different approach - don't repeat failed tools
- Be concise in your reasoning
- Stop after you've answered the question (don't keep using tools)
- Maximum 20 tool calls per query (to prevent infinite loops)

Let's get started!"""
    
    def call_openrouter(self) -> str:
        """
        Send messages to OpenRouter and get a response.
        
        WHY THIS API CALL:
        - OpenRouter abstracts multiple models (Claude, GPT, Llama, etc.)
        - We use 'openrouter/auto' to get the best free model
        - The API returns text that may contain tool calls
        
        Returns:
            The assistant's response text
        
        Raises:
            Exception if API call fails
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter requires this header
            "HTTP-Referer": "https://github.com/user/react-agent",
            "X-Title": "ReAct Agent",
        }
        
        payload = {
            "model": self.model,
            "messages": self.messages,
            "temperature": 0.7,  # Some randomness helps with diverse tool use
            "max_tokens": 1000,  # Limit response size
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data['choices'][0]['message']['content']
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter API error: {str(e)}")
        except KeyError as e:
            raise Exception(f"Unexpected API response format: {str(e)}")
    
    def run_agent(self, user_query: str) -> str:
        """
        Run the ReAct agent loop until it produces a final answer.
        
        THE LOOP (simplified):
            while not done:
                1. response = LLM(system_prompt + messages)
                2. tool_result = parse_and_execute_tool(response)
                3. if tool_result: add to messages and continue
                4. if "Final Answer" in response: return answer and stop
        
        This loop is POWERFUL because:
        - Agent can chain tools together
        - Each tool result informs the next action
        - Agent can recover from mistakes
        
        Args:
            user_query: The user's question
        
        Returns:
            The agent's final answer
        """
        
        # Initialize messages with system prompt
        self.messages = [
            {
                "role": "system",
                "content": self.get_system_prompt()
            },
            {
                "role": "user",
                "content": user_query
            }
        ]
        self.iteration_count = 0
        
        print(f"\n{'='*70}")
        print(f"STARTING REACT AGENT LOOP")
        print(f"{'='*70}")
        print(f"User Query: {user_query}\n")
        
        # Main loop
        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            print(f"\n--- ITERATION {self.iteration_count} ---")
            
            # STEP 1: Get LLM response
            print("Calling LLM...")
            try:
                llm_response = self.call_openrouter()
            except Exception as e:
                return f"ERROR: {str(e)}"
            
            print(f"\nLLM Response:\n{llm_response}\n")
            
            # STEP 2: Check if agent is done
            if "Final Answer:" in llm_response:
                # Extract the final answer
                answer = llm_response.split("Final Answer:")[-1].strip()
                print(f"{'='*70}")
                print(f"AGENT COMPLETE")
                print(f"{'='*70}")
                return answer
            
            # STEP 3: Parse and execute tool call
            print("Parsing for tool calls...")
            tool_result, parse_error = parse_and_execute_tool(llm_response)
            
            # STEP 4: Handle tool execution
            if parse_error:
                # Tool parsing or execution failed
                print(f"ERROR: {parse_error}")
                
                # Add error message to conversation so agent can learn
                self.messages.append({
                    "role": "assistant",
                    "content": llm_response
                })
                self.messages.append({
                    "role": "user",
                    "content": f"Error: {parse_error}\n\nPlease fix this error and try again."
                })
            
            elif tool_result is None:
                # No tool call detected
                print("No tool call detected. Adding response to context...")
                
                # Sometimes agent just wants to reason
                # Add response to messages and continue
                self.messages.append({
                    "role": "assistant",
                    "content": llm_response
                })
                self.messages.append({
                    "role": "user",
                    "content": "Continue. Either use a tool or provide the Final Answer."
                })
            
            else:
                # Tool executed successfully
                print(f"Tool Result: {json.dumps(tool_result, indent=2)}")
                
                # Add the LLM response and tool result to messages
                self.messages.append({
                    "role": "assistant",
                    "content": llm_response
                })
                self.messages.append({
                    "role": "user",
                    "content": f"Tool Result:\n{json.dumps(tool_result, indent=2)}"
                })
        
        # If we get here, we hit the iteration limit
        return f"ERROR: Reached maximum iterations ({self.max_iterations}). Agent got stuck in a loop."


def create_agent(api_key: Optional[str] = None) -> ReActAgent:
    """
    Factory function to create an agent with an API key.
    
    The API key is obtained from (in priority order):
    1. .env file (loaded by main.py at startup)
    2. OPENROUTER_API_KEY environment variable
    3. Argument passed to this function
    
    WHY .env FIRST:
    - Standard practice for development
    - Keeps secrets out of shell history
    - Easy to manage multiple keys
    
    Args:
        api_key: OpenRouter API key (if None, will look for OPENROUTER_API_KEY env var)
    
    Returns:
        Initialized ReActAgent
    """
    
    if not api_key:
        import os
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "No API key provided and OPENROUTER_API_KEY not found in .env or environment. "
                "Setup instructions:\n"
                "  1. Copy .env.example to .env\n"
                "  2. Edit .env with your OpenRouter API key\n"
                "  3. Run: python3 main.py\n"
                "Get a free key at https://openrouter.ai"
            )
    
    return ReActAgent(api_key)


if __name__ == "__main__":
    # Test the agent
    # This assumes .env file is set up with OPENROUTER_API_KEY
    import os
    from pathlib import Path
    
    # Try to load from .env
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in .env or environment")
        print("Setup: Copy .env.example to .env and add your API key")
        exit(1)
    
    agent = create_agent(api_key)
    
    # Test query
    query = "What's the weather in Paris and what recent earthquakes happened?"
    answer = agent.run_agent(query)
    print(f"\nFinal Answer:\n{answer}")
