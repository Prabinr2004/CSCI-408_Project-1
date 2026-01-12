"""
CLI INTERFACE - User interaction layer

This module provides a command-line interface for the ReAct agent.

WHY SEPARATE CLI FROM AGENT:
- Agent logic should be independent of how users interact with it
- Makes it easy to add other interfaces (web, API, Discord, etc.)
- Tests can call agent directly without CLI
- Clean separation of concerns
"""

import os
import sys
from pathlib import Path
from agent import create_agent


def load_env_file():
    """
    Load environment variables from .env file.
    
    This allows users to store their API key in .env instead of environment variable.
    Standard practice for keeping secrets separate from code.
    
    Returns:
        True if .env was loaded, False otherwise
    """
    env_path = Path(".env")
    
    if env_path.exists():
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            os.environ[key.strip()] = value.strip()
            return True
        except Exception as e:
            print(f"Warning: Could not load .env file: {str(e)}")
            return False
    return False


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def print_info(text: str):
    """Print informational text."""
    print(f"\n📝 {text}")


def print_success(text: str):
    """Print success message."""
    print(f"\n✅ {text}")


def print_error(text: str):
    """Print error message."""
    print(f"\n❌ {text}")


def get_api_key() -> str:
    """
    Get OpenRouter API key from .env file or environment variable.
    
    Priority order:
    1. Check .env file (loaded at startup)
    2. Check OPENROUTER_API_KEY environment variable
    3. Prompt user
    
    WHY THIS ORDER:
    - .env file is standard practice for development
    - Environment variable is standard for production
    - Prompt is fallback for first-time setup
    
    Returns:
        API key string
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    if api_key:
        # Could be from .env or environment variable
        if Path(".env").exists():
            print_success(f"Found API key in .env file")
        else:
            print_success(f"Found API key in OPENROUTER_API_KEY environment variable")
        return api_key
    
    print_error("OPENROUTER_API_KEY not found in .env or environment")
    print_info("Get a free API key at: https://openrouter.ai")
    
    api_key = input("\nEnter your OpenRouter API key: ").strip()
    
    if not api_key:
        print_error("No API key provided. Exiting.")
        sys.exit(1)
    
    return api_key


def get_example_queries() -> list:
    """
    Return example queries the user can try.
    
    These demonstrate different capabilities:
    - Weather tool (HTTP)
    - Earthquake tool (JSON parsing)
    - arXiv tool (complex API)
    - Calculator tool
    - Multi-step reasoning
    """
    return [
        "What's the weather in Tokyo?",
        "Show me recent earthquakes and calculate their average magnitude",
        "Search for papers about transformers and tell me how many you found",
        "Calculate 2^20 and tell me what that means",
        "What's the weather in New York and what's 98.6 in Celsius?",
    ]


def interactive_mode():
    """
    Run the agent in interactive mode.
    
    User can:
    1. Type queries (ask questions)
    2. See examples
    3. Exit cleanly
    4. View help
    """
    
    print_header("ReAct Agent - Interactive Mode")
    
    print_info("""
This is a ReAct (Reasoning + Acting) agent that can:
- Answer questions using multiple tools
- Chain operations together (weather + calculations, etc.)
- Reason through complex problems step by step

Examples of things to ask:
""")
    
    for i, example in enumerate(get_example_queries(), 1):
        print(f"  {i}. {example}")
    
    print_info("Type 'help' for commands, 'quit' to exit")
    
    # Get API key
    api_key = get_api_key()
    
    try:
        agent = create_agent(api_key)
        print_success("Agent initialized successfully!")
    except Exception as e:
        print_error(f"Failed to create agent: {str(e)}")
        sys.exit(1)
    
    # Main interaction loop
    query_count = 0
    
    while True:
        try:
            print("\n" + "-"*70)
            query = input("You: ").strip()
            
            if not query:
                continue
            
            # Handle commands
            if query.lower() == "quit":
                print_success("Goodbye!")
                break
            
            if query.lower() == "help":
                print_info("""
Commands:
  help   - Show this help message
  quit   - Exit the agent
  reset  - Start a new conversation

Type any question to ask the agent.
Example: "What's the weather in London?"
""")
                continue
            
            if query.lower() == "reset":
                print_info("Conversation reset. Starting fresh.")
                agent.messages = []
                continue
            
            if query.lower() == "examples":
                print_info("Example queries:")
                for i, example in enumerate(get_example_queries(), 1):
                    print(f"  {i}. {example}")
                continue
            
            # Process query
            query_count += 1
            
            print_info(f"Processing query #{query_count}...")
            
            try:
                answer = agent.run_agent(query)
                print_success(f"Agent Response:\n{answer}")
            except Exception as e:
                print_error(f"Agent error: {str(e)}")
        
        except KeyboardInterrupt:
            print_success("\nInterrupted. Exiting gracefully.")
            break
        except Exception as e:
            print_error(f"Unexpected error: {str(e)}")
            continue


def batch_mode(query: str):
    """
    Run the agent once with a specific query (non-interactive).
    
    Useful for:
    - Testing
    - Integration with other tools
    - Running from scripts
    
    Args:
        query: The user's question
    """
    
    print_header("ReAct Agent - Single Query")
    
    api_key = get_api_key()
    
    try:
        agent = create_agent(api_key)
        print_success("Agent initialized!")
    except Exception as e:
        print_error(f"Failed to create agent: {str(e)}")
        sys.exit(1)
    
    try:
        answer = agent.run_agent(query)
        print_success(f"Final Answer:\n{answer}")
    except Exception as e:
        print_error(f"Agent error: {str(e)}")
        sys.exit(1)


def main():
    """
    Main entry point for the CLI.
    
    Decides between:
    - Interactive mode: User can ask multiple questions
    - Batch mode: Run one query and exit
    
    First loads .env file if it exists.
    """
    # Load .env file at startup if it exists
    env_loaded = load_env_file()
    if env_loaded:
        print_info("Loaded API key from .env file")
    
    if len(sys.argv) > 1:
        # Batch mode: python main.py "your query here"
        query = " ".join(sys.argv[1:])
        batch_mode(query)
    else:
        # Interactive mode: python main.py
        interactive_mode()


if __name__ == "__main__":
    main()
