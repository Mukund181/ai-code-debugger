import os
import sys
from dotenv import load_dotenv

# Ensure the root folder is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.core import build_agent, build_gen_agent

def test_debug_agent():
    print("TESTING DEBUGER AGENT WORKFLOW")
    agent = build_agent()
    
    # Buggy code representing a division by zero logic error
    test_code = """
def divide_items(items, divisor):
    # This will raise a ZeroDivisionError if divisor is 0
    return [x / divisor for x in items]

print(divide_items([10, 20, 30], 0))
"""
    
    test_input = f"Debug this code:\n```python\n{test_code}\n```\n\nError traceback:\n```\nZeroDivisionError: division by zero\n```"
    
    try:
        response = agent.invoke({"input": test_input})
        
        print("\n--- Agent Response Steps ---")
        for i, step in enumerate(response.get("steps", [])):
            print(f"Step {i+1}: {step['name']} [{step['status'].upper()}]")
            print(f"       Detail: {step['detail'][:120]}...")
            
        print("\n--- Final Explanation & Fix (Partial) ---")
        output = response.get("output", "No response.")
        print(output[:300] + "...\n[TRUNCATED]")
        
        print("\n--- Last Sandbox Execution Result ---")
        print(response.get("execution_result", "None").strip())
        
        print("\nDebugger Agent test successful!")
    except Exception as e:
        print(f"ERROR: Debugger Agent test failed: {str(e)}", file=sys.stderr)


def test_generation_agent():
    print("TESTING GENERATION & LEARNING AGENT WORKFLOW")
    agent = build_gen_agent()
    
    prompt = "Write a Python class representing a Stack data structure with push and pop methods, and a sample run."
    topic = "Data Structures"
    
    try:
        response = agent.invoke({"input": prompt, "topic": topic})
        
        print("\n--- Agent Response Steps ---")
        for i, step in enumerate(response.get("steps", [])):
            print(f"Step {i+1}: {step['name']} [{step['status'].upper()}]")
            print(f"       Detail: {step['detail'][:120]}...")
            
        print("\n--- Final Output Tutorial (Partial) ---")
        output = response.get("output", "No response.")
        print(output[:300] + "...\n[TRUNCATED]")
        
        print("\n--- Sandbox Verification Output ---")
        print(response.get("execution_result", "None").strip())
        
        print("\nGeneration Agent test successful!")
    except Exception as e:
        print(f"ERROR: Generation Agent test failed: {str(e)}", file=sys.stderr)


if __name__ == "__main__":
    load_dotenv()
    test_debug_agent()
    test_generation_agent()
