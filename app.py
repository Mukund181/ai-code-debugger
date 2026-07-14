import sys

print("==========================================================================")
print("WARNING: The Streamlit frontend has been removed.")
print("The AI Code Debugger is now served via FastAPI and a static HTML frontend.")
print("==========================================================================")
print("\nTo start the server, please run:")
print("    uvicorn main:app --reload")
print("\nAnd open your web browser to:")
print("    http://127.0.0.1:8000")
print("==========================================================================")

sys.exit(1)