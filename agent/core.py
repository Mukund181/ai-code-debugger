import os
import re
from dotenv import load_dotenv
from groq import Groq
from agent.tools import classify_error, retrieve_docs, execute_code

load_dotenv()

_agent = None

def build_agent():
    global _agent
    if _agent is None:
        _agent = DebugAgent()
    return _agent


class DebugAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model  = "llama-3.1-8b-instant"

    def invoke(self, inputs: dict) -> dict:
        user_input = inputs.get("input", "")
        steps = []

        # Step 1: Classify Error Type
        steps.append({
            "name": "Classify Error",
            "status": "pending",
            "detail": "Analyzing user query and matching error patterns..."
        })
        error_type = "unknown"
        if any(k in user_input.lower() for k in ["error", "exception", "traceback", "bug"]):
            try:
                error_type = classify_error.invoke(user_input)
                steps[-1]["status"] = "success"
                steps[-1]["detail"] = f"Classified as error category: {error_type}"
            except Exception as e:
                steps[-1]["status"] = "failed"
                steps[-1]["detail"] = f"Classification failed ({str(e)}), continuing with unknown."
        else:
            steps[-1]["status"] = "success"
            steps[-1]["detail"] = "No standard crash stack trace found. Treating as logic error or general inquiry."
            error_type = "logic_error"

        # Step 2: Retrieve Relevant Docs (RAG)
        steps.append({
            "name": "Retrieve Reference Docs",
            "status": "pending",
            "detail": "Searching RAG database for matching concepts..."
        })
        try:
            retrieved = retrieve_docs.invoke(user_input)[:800]
            steps[-1]["status"] = "success"
            steps[-1]["detail"] = "Successfully retrieved reference documentation from vector database."
        except Exception as e:
            retrieved = ""
            steps[-1]["status"] = "failed"
            steps[-1]["detail"] = f"RAG retrieval failed ({str(e)}), proceeding without local docs."

        # Step 3: Generate Draft Solution
        steps.append({
            "name": "Draft Code Fix",
            "status": "pending",
            "detail": "Asking Groq LLM to analyze and write a solution..."
        })
        
        prompt = f"""You are an expert Python debugging assistant.
Relevant reference documentation:
{retrieved}

Detected error category: {error_type}

User Code and/or Error query:
{user_input}

Please write a Python code snippet that fixes the issue, enclosed in a ```python ... ``` block. Also explain:
1) What is wrong
2) How you fixed it
3) Why the issue occurred

Make sure the code block is standalone and can be executed to verify its correctness.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Python debugging assistant. Be concise and write functional python code in markdown blocks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            current_explanation = response.choices[0].message.content
            steps[-1]["status"] = "success"
            steps[-1]["detail"] = "Draft correction and explanation successfully generated."
        except Exception as e:
            steps[-1]["status"] = "failed"
            steps[-1]["detail"] = f"Failed to generate initial draft: {str(e)}"
            return {
                "output": "Error: Failed to contact the AI model.",
                "steps": steps,
                "error_type": error_type,
                "execution_result": ""
            }

        # Step 4: Sandbox execution self-correction loop
        steps.append({
            "name": "Sandbox Verification & Self-Correction",
            "status": "pending",
            "detail": "Extracting code block and executing in sandbox..."
        })

        max_attempts = 3
        success = False
        exec_details = ""
        
        for attempt in range(1, max_attempts + 1):
            # Extract code block from explanation
            code_blocks = re.findall(r"```python\n(.*?)```", current_explanation, re.DOTALL)
            if not code_blocks:
                code_blocks = re.findall(r"```\n(.*?)```", current_explanation, re.DOTALL)
                
            if not code_blocks:
                exec_details = "No executable code blocks found. Skipping sandbox execution check."
                success = True  # Nothing to verify, treated as informational response
                break

            current_code = code_blocks[0]
            steps[-1]["detail"] = f"Running code verification (Attempt {attempt}/{max_attempts})..."

            try:
                exec_details = execute_code.invoke(current_code)
            except Exception as e:
                exec_details = f"ERROR: Subprocess run failed: {str(e)}"

            # Detect failure signatures
            has_error = "ERROR" in exec_details or "Traceback" in exec_details or "Exception" in exec_details
            
            if not has_error:
                success = True
                steps[-1]["detail"] = f"Attempt {attempt}: Code ran successfully without errors!"
                break
            else:
                # Self-correction prompt
                steps[-1]["detail"] = f"Attempt {attempt} failed. Traceback detected! Asking LLM to self-correct..."
                correction_prompt = f"""The previous code snippet you wrote caused an execution error.
Execution Error:
{exec_details}

Here was the code that failed:
```python
{current_code}
```

Please analyze the execution error and write a corrected version of the code inside a new ```python ... ``` block, along with a revised explanation. Ensure all necessary variables, modules, and inputs are defined so it can run standalone.
"""
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are an expert Python debugging assistant. Your last code snippet had an execution error. Fix it."},
                            {"role": "user", "content": correction_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=1024,
                    )
                    current_explanation = response.choices[0].message.content
                except Exception as e:
                    exec_details += f"\n(Correction call failed: {str(e)})"
                    break

        if success:
            steps[-1]["status"] = "success"
            steps[-1]["detail"] = f"Code verified successfully.\n\nSandbox Execution Output:\n{exec_details}"
        else:
            steps[-1]["status"] = "failed"
            steps[-1]["detail"] = f"Failed to correct the code within {max_attempts} attempts.\n\nLast Sandbox Execution Output:\n{exec_details}"

        return {
            "output": current_explanation,
            "steps": steps,
            "error_type": error_type,
            "execution_result": exec_details
        }