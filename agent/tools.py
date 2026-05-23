import subprocess
import sys
import tempfile
import os
from langchain_core.tools import tool
from classifier.predict import classify_error as _classify
from rag.embedder import retrieve as _retrieve

@tool
def classify_error(error_text: str) -> str:
    """Classify a Python error message into a category."""
    return _classify(error_text)

@tool
def retrieve_docs(query: str) -> str:
    """Retrieve relevant documentation for a given error or concept."""
    return _retrieve(query)

@tool
def execute_code(code: str) -> str:
    """Execute a Python code snippet and return its output or error."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
        f.write(code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, fname],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout or ""
        error  = result.stderr or ""
        return f"OUTPUT:\n{output}\nERROR:\n{error}" if error else f"OUTPUT:\n{output}"
    except subprocess.TimeoutExpired:
        return "ERROR: Code execution timed out (10s limit)."
    finally:
        os.unlink(fname)