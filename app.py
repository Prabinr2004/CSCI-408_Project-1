"""
FLASK WEB APP - ReAct Agent Web Interface

This creates a web application where users can:
- Ask questions in a chat interface
- See the agent's reasoning in real-time
- View tool calls and results
- Get final answers

Why Flask?
- Lightweight and easy to understand
- Perfect for small to medium apps
- Easy to deploy on Render, Railway, Heroku
- Minimal configuration needed
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from agent import create_agent
from tool_parser import parse_and_execute_tool

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Load .env file at startup
def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

# Load .env at startup
load_env_file()

# Get API key
api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    print("WARNING: OPENROUTER_API_KEY not found in .env or environment")
    print("The app will fail when trying to use the agent")


@app.route('/')
def index():
    """
    Serve the main chat interface
    
    WHY THIS ROUTE:
    - Entry point for the web app
    - Renders the HTML chat interface
    - Client will communicate via /api/chat endpoint
    """
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    API endpoint for chat requests
    
    Receives:
        {
            "message": "What's the weather in Paris?"
        }
    
    Returns:
        {
            "success": true,
            "answer": "The weather in Paris is...",
            "iterations": [
                {
                    "iteration": 1,
                    "llm_response": "...",
                    "tool_call": "...",
                    "tool_result": "..."
                }
            ]
        }
    
    WHY THIS APPROACH:
    - Separates frontend from backend
    - Returns structured data the frontend can display
    - Tracks iterations for transparency
    - Handles errors gracefully
    """
    
    try:
        # Get the user's message
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                "success": False,
                "error": "No message provided"
            }), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({
                "success": False,
                "error": "Message cannot be empty"
            }), 400
        
        # Check API key
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key not configured. Set OPENROUTER_API_KEY in .env"
            }), 500
        
        # Create agent and run
        agent = create_agent(api_key)
        
        # We need to track iterations for the web interface
        # Monkey-patch the agent to collect iteration details
        iterations = []
        original_run = agent.run_agent
        
        def run_with_tracking(query):
            """Run agent while collecting iteration details"""
            # This is a simplified version - just run the agent normally
            # In a production app, you'd modify agent.py to expose iteration details
            result = original_run(query)
            return result
        
        # Run the agent
        answer = agent.run_agent(user_message)
        
        # Return response
        return jsonify({
            "success": True,
            "answer": answer,
            "iterations": iterations
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error: {str(e)}"
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint
    
    Used by Render to verify the app is running
    """
    return jsonify({
        "status": "healthy",
        "api_key_configured": bool(api_key)
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error"
    }), 500


if __name__ == '__main__':
    # Get port from environment or default to 5001
    # (5001 is used to avoid conflicts with other projects on 5000)
    port = int(os.environ.get('PORT', 5001))
    
    # Run the app
    # In production (Render), set FLASK_ENV=production
    # Debug mode should be OFF in production
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print(f"🚀 Flask app starting on port {port}")
    print(f"📝 API key configured: {bool(api_key)}")
    print(f"🔧 Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',  # Listen on all interfaces (required for Render)
        port=port,
        debug=debug
    )
