"""
TOOL PARSER MODULE - Parse tool calls from LLM output

The ReAct agent loop sends a prompt to the LLM and gets back text that may include:
1. Reasoning (the agent's internal thoughts)
2. A tool call (if it decides to use a tool)
3. A final answer (if it decides to stop)

This module extracts tool calls from the LLM's text response.

WHY THIS IS TRICKY:
- The LLM can output tool calls in different formats
- Tool names might be misspelled
- Arguments might be missing or malformed
- The LLM might output multiple tool calls
- The LLM might output no tool calls (just reasoning)

FAILURE MODES WE HANDLE:
1. Invalid JSON: LLM might output broken JSON
2. Misspelled tool names: "get_weater" instead of "get_weather"
3. Missing arguments: "get_weather()" instead of "get_weather('location')"
4. Wrong number of arguments: "get_weather('a', 'b')" when it takes 1 arg
"""

import re
import json
from typing import Optional, Tuple, Any, Dict
from tools import TOOLS


class ToolCall:
    """Represents a single tool call extracted from LLM output."""
    
    def __init__(self, tool_name: str, arguments: Dict[str, Any]):
        self.tool_name = tool_name
        self.arguments = arguments
    
    def __repr__(self):
        return f"ToolCall({self.tool_name}, {self.arguments})"


def extract_tool_calls(text: str) -> Tuple[Optional[ToolCall], str]:
    """
    Extract a tool call from LLM output text.
    
    The LLM will output text like:
        "I should search for papers on machine learning.
         
         Tool: search_arxiv
         Arguments: {"query": "machine learning", "max_results": "10"}"
    
    We need to parse this and extract the tool call.
    
    WHY THIS FORMAT:
    - We're teaching the LLM a specific format to follow
    - It's easier than parsing arbitrary function calls
    - The LLM can still do reasoning before calling the tool
    
    Args:
        text: The complete LLM response
    
    Returns:
        Tuple of (ToolCall or None, error_message)
        - If tool found: (ToolCall object, "")
        - If no tool: (None, "")
        - If parsing failed: (None, error_message)
    """
    
    # Pattern 1: Look for "Tool: <name>\nArguments: <json>"
    tool_pattern = r"Tool:\s*(\w+)\s*\n\s*Arguments:\s*({.*?})"
    matches = re.findall(tool_pattern, text, re.DOTALL)
    
    if not matches:
        # No tool call found - agent might be done or just reasoning
        return None, ""
    
    # Get the LAST tool call (in case there are multiple)
    tool_name, args_json = matches[-1]
    
    # FAILURE MODE 1: Invalid JSON
    try:
        arguments = json.loads(args_json)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in tool arguments: {str(e)}"
    
    # FAILURE MODE 2: Misspelled tool name
    if tool_name not in TOOLS:
        available = ", ".join(TOOLS.keys())
        return None, f"Unknown tool '{tool_name}'. Available: {available}"
    
    return ToolCall(tool_name, arguments), ""


def execute_tool(tool_call: ToolCall) -> Tuple[Any, str]:
    """
    Execute a tool call and return its result.
    
    FAILURE MODE 3 & 4: Missing or wrong arguments
    We try to call the tool and catch exceptions if arguments don't match.
    
    Args:
        tool_call: The ToolCall to execute
    
    Returns:
        Tuple of (result, error_message)
        - If successful: (result_dict, "")
        - If failed: (None, error_message)
    """
    
    try:
        tool_func = TOOLS[tool_call.tool_name]
        
        # Call the tool with its arguments
        # The tool function should handle any API errors internally
        result = tool_func(**tool_call.arguments)
        
        return result, ""
    
    except TypeError as e:
        # Wrong number of arguments
        return None, f"Tool {tool_call.tool_name} argument error: {str(e)}"
    except Exception as e:
        return None, f"Tool execution error: {str(e)}"


def parse_and_execute_tool(text: str) -> Tuple[Optional[Dict], str]:
    """
    Combined function: extract a tool call and execute it.
    
    Returns:
        Tuple of (tool_result, error_message)
        - If tool executed: (result_dict, "")
        - If no tool in output: (None, "")
        - If error: (None, error_message)
    """
    
    tool_call, parse_error = extract_tool_calls(text)
    
    if parse_error:
        return None, parse_error
    
    if tool_call is None:
        # No tool call found - not an error, just no tool
        return None, ""
    
    result, exec_error = execute_tool(tool_call)
    
    if exec_error:
        return None, exec_error
    
    return result, ""


# ============================================================================
# TESTING: Pattern matching
# ============================================================================

if __name__ == "__main__":
    # Test examples
    test_cases = [
        # Valid tool call
        """I should check the weather in Paris.
        
Tool: get_weather
Arguments: {"location": "Paris, France"}""",
        
        # Tool with multiple arguments
        """Let me search for papers on AI.
        
Tool: search_arxiv
Arguments: {"query": "artificial intelligence", "max_results": "10"}""",
        
        # Invalid JSON
        """Tool: search_arxiv
Arguments: {"query": "test" missing_colon 5}""",
        
        # Misspelled tool
        """Tool: get_wheather
Arguments: {"location": "NYC"}""",
        
        # No tool call
        """This is just reasoning text with no tool.""",
    ]
    
    for i, test_text in enumerate(test_cases):
        print(f"\n--- Test {i+1} ---")
        print(f"Input: {test_text[:50]}...")
        tool_call, error = extract_tool_calls(test_text)
        if error:
            print(f"Error: {error}")
        elif tool_call:
            print(f"Extracted: {tool_call}")
        else:
            print("No tool call found")
