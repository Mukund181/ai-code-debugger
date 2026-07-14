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


def test_repo_analyzer():
    print("TESTING LOCAL GRAPH RAG DEPENDENCY MAPPER")    
    import tempfile
    import shutil
    from repo_analyzer.graph_rag import CodeGraph
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Create helper module
        helper_code = """
def add_values(x, y):
    return x + y

def multiply_values(x, y):
    return x * y
"""
        with open(os.path.join(temp_dir, "math_helper.py"), "w", encoding="utf-8") as f:
            f.write(helper_code)
            
        # Create main application calling helper
        app_code = """
from math_helper import add_values

def execute_logic():
    val = add_values(10, 20)
    print("Result:", val)
    return val

if __name__ == "__main__":
    execute_logic()
"""
        with open(os.path.join(temp_dir, "main_app.py"), "w", encoding="utf-8") as f:
            f.write(app_code)
            
        graph = CodeGraph()
        print("Parsing dummy workspace directory...")
        graph.build_from_directory(temp_dir)
        
        print(f"Graph nodes parsed: {list(graph.nodes.keys())}")
        print(f"Graph edges mapped: {graph.edges}")
        
        # Query impact of math_helper.py change
        print("\nQuerying impact chain of 'math_helper.py' changes...")
        impact = graph.query_impact("math_helper.py")
        
        print("Root file:", impact["root_file"])
        print("Root nodes:", impact["root_nodes"])
        print("Impact chain:")
        for idx, item in enumerate(impact["impact_chain"]):
            print(f"  {idx+1}: {item['type']} '{item['name']}' in file '{item['file']}' (Depth: {item['depth']})")
            
        assert len(impact["impact_chain"]) > 0, "Dependency mapping failed to detect any connections!"
        print("\nGraph RAG tests successful!")
    except Exception as e:
        print(f"ERROR: Graph RAG testing failed: {str(e)}", file=sys.stderr)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    load_dotenv()
    test_debug_agent()
    test_generation_agent()
    test_repo_analyzer()
