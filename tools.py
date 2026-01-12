"""
TOOLS MODULE - Tool definitions and implementations

This module defines all available tools the ReAct agent can use.
Each tool is a function that:
1. Takes arguments from the agent
2. Makes external API calls (HTTP requests)
3. Returns structured data (dict/string) for the agent to process

WHY THIS DESIGN:
- Separates tool logic from agent logic (clean architecture)
- Easy to add/remove tools without changing the agent
- Tools return JSON-serializable data so agent can reason about results
"""

import requests
import json
from typing import Any, Dict

# Tool registry - agent will search this dict by tool name
TOOLS = {}


def register_tool(func):
    """Decorator to register a tool in the TOOLS dictionary."""
    TOOLS[func.__name__] = func
    return func


# ============================================================================
# TOOL 1: Weather API (HTTP request)
# ============================================================================
@register_tool
def get_weather(location: str) -> Dict[str, Any]:
    """
    Get current weather for a location using NOAA API.
    
    WHY THIS TOOL:
    - Teaches HTTP requests to external APIs
    - Returns structured data the agent must interpret
    - Real-world use case
    
    Args:
        location: City, State format (e.g., "San Francisco, CA")
    
    Returns:
        dict with temperature, humidity, conditions
    """
    try:
        # NOAA requires coordinates; use a lookup service
        # For simplicity, we'll use a free weather API (wttr.in)
        response = requests.get(
            f"https://wttr.in/{location}?format=j1",
            timeout=5
        )
        response.raise_for_status()
        
        data = response.json()
        current = data['current_condition'][0]
        
        return {
            "success": True,
            "location": location,
            "temperature_c": current['temp_C'],
            "temperature_f": current['temp_F'],
            "humidity": current['humidity'],
            "conditions": current['weatherDesc'][0]['value'],
            "wind_kph": current['windspeedKmph']
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch weather: {str(e)}"
        }
    except (KeyError, json.JSONDecodeError) as e:
        return {
            "success": False,
            "error": f"Failed to parse weather data: {str(e)}"
        }


# ============================================================================
# TOOL 2: Earthquake Data API (HTTP request + structured JSON)
# ============================================================================
@register_tool
def get_recent_earthquakes(region: str = "US") -> Dict[str, Any]:
    """
    Get recent earthquake data from USGS API.
    
    WHY THIS TOOL:
    - Teaches querying JSON APIs
    - Returns structured array data
    - Agent must process multiple records
    
    Args:
        region: Geographic region filter (e.g., "US", "California")
    
    Returns:
        dict with list of recent earthquakes
    """
    try:
        # USGS Earthquake Hazards API
        response = requests.get(
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
            timeout=5
        )
        response.raise_for_status()
        
        data = response.json()
        earthquakes = []
        
        # Parse the features array
        for feature in data['features'][:5]:  # Limit to 5 most recent
            props = feature['properties']
            coords = feature['geometry']['coordinates']
            
            earthquakes.append({
                "magnitude": props['mag'],
                "location": props['place'],
                "depth_km": coords[2],
                "latitude": coords[1],
                "longitude": coords[0],
                "timestamp": props['time'],
                "type": props.get('type', 'unknown')
            })
        
        return {
            "success": True,
            "count": len(earthquakes),
            "earthquakes": earthquakes
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch earthquake data: {str(e)}"
        }
    except (KeyError, json.JSONDecodeError) as e:
        return {
            "success": False,
            "error": f"Failed to parse earthquake data: {str(e)}"
        }


# ============================================================================
# TOOL 3: arXiv Paper Search (HTTP + JSON parsing)
# ============================================================================
@register_tool
def search_arxiv(query: str, max_results: str = "5") -> Dict[str, Any]:
    """
    Search arXiv papers by keyword.
    
    WHY THIS TOOL:
    - Teaches parsing complex JSON responses
    - Agent must extract specific fields
    - Real academic data
    
    Args:
        query: Search term(s) (e.g., "machine learning", "quantum computing")
        max_results: Number of results to return (default: 5)
    
    Returns:
        dict with list of papers including title, authors, abstract
    """
    try:
        max_results = int(max_results) if max_results.isdigit() else 5
        
        # arXiv API endpoint
        response = requests.get(
            "http://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{query}",
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            },
            timeout=5
        )
        response.raise_for_status()
        
        # Parse XML response (arXiv returns Atom XML)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        papers = []
        # XML namespace for Atom
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text
            authors_elem = entry.findall('atom:author', ns)
            authors = [a.find('atom:name', ns).text for a in authors_elem[:3]]
            summary = entry.find('atom:summary', ns).text.strip()
            published = entry.find('atom:published', ns).text
            paper_id = entry.find('atom:id', ns).text.split('/abs/')[-1]
            
            papers.append({
                "title": title,
                "authors": authors,
                "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                "published": published[:10],  # Just the date
                "arxiv_id": paper_id
            })
        
        return {
            "success": True,
            "query": query,
            "count": len(papers),
            "papers": papers
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to search arXiv: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse arXiv results: {str(e)}"
        }


# ============================================================================
# TOOL 4: Calculator (no HTTP, pure logic, but structured output)
# ============================================================================
@register_tool
def calculate(expression: str) -> Dict[str, Any]:
    """
    Evaluate a mathematical expression safely.
    
    WHY THIS TOOL:
    - Teaches agent to use a simple local tool
    - Returns structured result
    - Example of synchronous tool execution
    
    SAFETY NOTE:
    - We use eval() with a restricted namespace (dangerous in production!)
    - In real systems, use a proper math parser or sympy
    - Here we restrict to safe math operations only
    
    Args:
        expression: Math expression (e.g., "2 + 2", "sqrt(16)", "3.14 * 5")
    
    Returns:
        dict with calculation result
    """
    try:
        # Restricted namespace for eval - only allow safe math functions
        import math
        safe_dict = {
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'sqrt': math.sqrt,
            'log': math.log,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e,
        }
        
        # Check for potentially dangerous code
        dangerous_keywords = ['import', '__', 'open', 'exec', 'compile']
        if any(keyword in expression.lower() for keyword in dangerous_keywords):
            return {
                "success": False,
                "error": "Expression contains restricted keywords"
            }
        
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        
        return {
            "success": True,
            "expression": expression,
            "result": float(result),
            "result_type": type(result).__name__
        }
    except ZeroDivisionError:
        return {
            "success": False,
            "error": "Division by zero"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Invalid expression: {str(e)}"
        }


# ============================================================================
# HELPER FUNCTION: Get tool description for system prompt
# ============================================================================
def get_tools_description() -> str:
    """
    Generate a description of all available tools for the system prompt.
    
    WHY: The LLM needs to know what tools are available and how to use them.
    This is auto-generated from the tool registry so we don't repeat ourselves.
    """
    description = "You have access to these tools:\n\n"
    
    tools_info = {
        "get_weather": {
            "description": "Get current weather for a location",
            "example": 'get_weather("San Francisco, CA")'
        },
        "get_recent_earthquakes": {
            "description": "Get recent earthquake data",
            "example": 'get_recent_earthquakes()'
        },
        "search_arxiv": {
            "description": "Search academic papers on arXiv",
            "example": 'search_arxiv("machine learning", "10")'
        },
        "calculate": {
            "description": "Evaluate mathematical expressions",
            "example": 'calculate("2 ** 10")'
        }
    }
    
    for tool_name, info in tools_info.items():
        description += f"- {tool_name}: {info['description']}\n"
        description += f"  Example: {info['example']}\n"
    
    return description


if __name__ == "__main__":
    # Quick test of tools when run directly
    print("Testing tools...")
    print("\n1. Weather:")
    print(json.dumps(get_weather("London"), indent=2))
    print("\n2. Earthquakes:")
    print(json.dumps(get_recent_earthquakes(), indent=2))
    print("\n3. arXiv:")
    print(json.dumps(search_arxiv("transformer", "3"), indent=2))
    print("\n4. Calculator:")
    print(json.dumps(calculate("sqrt(16) + 2 ** 3"), indent=2))
