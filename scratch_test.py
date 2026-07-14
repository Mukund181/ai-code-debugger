import os
import sys
from dotenv import load_dotenv

# Ensure the root folder is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.core import build_agent

def test_agent_workflow():
    print("Initializing self-correcting agent test...")
    agent = build_agent()
    
    # Buggy code representing a division by zero logic error
    test_code = """
def divide_items(items, divisor):
    # This will raise a ZeroDivisionError if divisor is 0
    return [x / divisor for x in items]

print(divide_items([10, 20, 30], 0))
"""
    
    test_input = f"Debug this code:\n```python\n{test_code}\n```\n\nError traceback:\n```\nZeroDivisionError: division by zero\n```"
    
    print("\n--- Sending Input to Agent ---")
    print(test_input)
    print("------------------------------")
    
    try:
        response = agent.invoke({"input": test_input})
        
        print("\n--- Agent Response Steps ---")
        for i, step in enumerate(response.get("steps", [])):
            print(f"Step {i+1}: {step['name']} [{step['status'].upper()}]")
            print(f"       Detail: {step['detail'][:150]}...")
            
        print("\n--- Final Explanation & Fix ---")
        print(response.get("output", "No response."))
        
        print("\n--- Last Sandbox Execution Result ---")
        print(response.get("execution_result", "None"))
        
        print("\nTest run complete!")
    except Exception as e:
        print(f"ERROR: Agent workflow test encountered an error: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    load_dotenv()
    test_agent_workflow()
