import os
import re
from dotenv import load_dotenv
from groq import Groq
from agent.tools import classify_error, retrieve_docs, execute_code

load_dotenv()

_agent = None
_gen_agent = None

def build_agent():
    global _agent
    if _agent is None:
        _agent = DebugAgent()
    return _agent

def build_gen_agent():
    global _gen_agent
    if _gen_agent is None:
        _gen_agent = GenerationAgent()
    return _gen_agent


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
        
        prompt = f"""You are an expert multi-language debugging assistant. You support Python, C++, Java, JavaScript, and other languages.
Relevant reference documentation:
{retrieved}

Detected error category: {error_type}

User Code and/or Error query:
{user_input}

Please write a code snippet in the target language (default to Python if not specified) that fixes the issue, enclosed in a standard markdown ```[language] ... ``` block (e.g. ```cpp for C++ or ```python for Python). Also explain:
1) What is wrong
2) How you fixed it
3) Why the issue occurred

Make sure the code block is standalone and correct.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert multi-language debugging assistant. Be concise and write functional code in markdown blocks."},
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
            # Extract code block and language tag: e.g. ```cpp\ncode\n```
            code_blocks = re.findall(r"```(\w*)\n(.*?)```", current_explanation, re.DOTALL)
            if not code_blocks:
                exec_details = "No code blocks found. Skipping sandbox execution check."
                success = True  
                break

            lang, current_code = code_blocks[0]
            lang = lang.strip().lower()

            if not lang:
                lang = "python"

            # Execute Python code blocks in sandbox
            if lang in ["python", "py"]:
                steps[-1]["detail"] = f"Running python code verification (Attempt {attempt}/{max_attempts})..."
                try:
                    exec_details = execute_code.invoke(current_code)
                except Exception as e:
                    exec_details = f"ERROR: Subprocess run failed: {str(e)}"

                has_error = "ERROR" in exec_details or "Traceback" in exec_details or "Exception" in exec_details
                
                if not has_error:
                    success = True
                    steps[-1]["detail"] = f"Attempt {attempt}: Code ran successfully without errors!"
                    break
                else:
                    steps[-1]["detail"] = f"Attempt {attempt} failed. Traceback detected! Asking LLM to self-correct..."
                    correction_prompt = f"""The previous Python code snippet you wrote caused an execution error.
Execution Error:
{exec_details}

Here was the code that failed:
```python
{current_code}
```

Please analyze the execution error and write a corrected version of the code inside a new ```python ... ``` block, along with a revised explanation.
"""
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": "You are an expert Python debugging assistant. Correct the code so it executes successfully."},
                                {"role": "user", "content": correction_prompt}
                            ],
                            temperature=0.1,
                            max_tokens=1024,
                        )
                        current_explanation = response.choices[0].message.content
                    except Exception as e:
                        exec_details += f"\n(Correction call failed: {str(e)})"
                        break
            else:
                # Non-python code, skip compilation run checks to avoid syntax exceptions
                exec_details = f"Compilation check bypassed for non-Python language: {lang}."
                success = True
                steps[-1]["detail"] = f"Skipped sandbox check (non-Python language: {lang}). Code assumed correct."
                break

        if success:
            steps[-1]["status"] = "success"
            steps[-1]["detail"] = f"Code verified successfully.\n\n{exec_details}"
        else:
            steps[-1]["status"] = "failed"
            steps[-1]["detail"] = f"Failed to correct the code within {max_attempts} attempts.\n\n{exec_details}"

        return {
            "output": current_explanation,
            "steps": steps,
            "error_type": error_type,
            "execution_result": exec_details
        }


class GenerationAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model  = "llama-3.1-8b-instant"

    def invoke(self, inputs: dict) -> dict:
        prompt_input = inputs.get("input", "")
        topic        = inputs.get("topic", "")
        steps        = []

        # Step 1: Search Concept Database
        steps.append({
            "name": "Search Concept Database",
            "status": "pending",
            "detail": f"Searching RAG vector store for material on '{prompt_input}'..."
        })
        try:
            query = f"{topic} {prompt_input}" if topic else prompt_input
            retrieved = retrieve_docs.invoke(query)[:800]
            steps[-1]["status"] = "success"
            steps[-1]["detail"] = "Retrieved instructional material from vector database."
        except Exception as e:
            retrieved = ""
            steps[-1]["status"] = "failed"
            steps[-1]["detail"] = f"RAG query failed ({str(e)}), proceeding without local database guides."

        # Step 2: Write Code & Learning Guide
        steps.append({
            "name": "Write Code & Learning Guide",
            "status": "pending",
            "detail": "Asking Groq LLM to generate code and concepts tutorial..."
        })

        system_prompt = (
            "You are an expert computer science instructor and code generator. "
            "You support Python, C++, Java, JavaScript, and other languages. "
            "Write highly clear, self-contained code in standard markdown ```[language] ... ``` blocks (e.g. ```cpp or ```python), "
            "followed by a detailed conceptual tutorial explaining the logic, the computational principles, "
            "and complexity (Time and Space complexity using Big-O notation)."
        )

        user_prompt = f"""Write a script in the target language (check if the user requested C++, Java, JS, or Python) to solve this prompt:
"{prompt_input}"

Category / Topic context: {topic}
Reference documentation:
{retrieved}

Ensure the code:
1. Is written in the requested programming language (e.g., C++ if prompt contains 'c++', 'cpp' or 'cplusplus').
2. Is complete, fully functional, and standalone.
3. Is enclosed in a standard markdown ```[language] ... ``` block.

Also provide a brief educational guide below the code block:
- Explanation of how it works.
- Key computer science concepts involved.
- Big-O Time & Space Complexity analysis.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            current_explanation = response.choices[0].message.content
            steps[-1]["status"] = "success"
            steps[-1]["detail"] = "Generated code snippet and CS concept tutorial."
        except Exception as e:
            steps[-1]["status"] = "failed"
            steps[-1]["detail"] = f"LLM generation failed: {str(e)}"
            return {
                "output": "Error: Failed to contact AI model.",
                "steps": steps,
                "execution_result": ""
            }

        # Step 3: Sandbox Verification & Self-Correction
        steps.append({
            "name": "Sandbox Verification & Self-Correction",
            "status": "pending",
            "detail": "Extracting generated code and compiling in sandbox..."
        })

        max_attempts = 3
        success = False
        exec_details = ""

        for attempt in range(1, max_attempts + 1):
            # Extract code block and language tag
            code_blocks = re.findall(r"```(\w*)\n(.*?)```", current_explanation, re.DOTALL)
            if not code_blocks:
                exec_details = "No executable code blocks found to verify."
                success = True
                break

            lang, current_code = code_blocks[0]
            lang = lang.strip().lower()

            if not lang:
                lang = "python"

            if lang in ["python", "py"]:
                steps[-1]["detail"] = f"Running python code verification (Attempt {attempt}/{max_attempts})..."
                try:
                    exec_details = execute_code.invoke(current_code)
                except Exception as e:
                    exec_details = f"ERROR: Subprocess run failed: {str(e)}"

                has_error = "ERROR" in exec_details or "Traceback" in exec_details or "Exception" in exec_details

                if not has_error:
                    success = True
                    steps[-1]["detail"] = f"Attempt {attempt}: Code compiled and executed successfully!"
                    break
                else:
                    steps[-1]["detail"] = f"Attempt {attempt} failed. Compilation/Execution error! Asking LLM to self-correct..."
                    correction_prompt = f"""The Python script you wrote has execution errors.
Execution Error:
{exec_details}

Here was the code:
```python
{current_code}
```

Please analyze the execution error and write a corrected version of the code inside a new ```python ... ``` block, keeping the tutorial explanation intact. Ensure all variables and modules are defined.
"""
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": "You are an expert Python debugging assistant. Correct the code you generated so it executes without error."},
                                {"role": "user", "content": correction_prompt}
                            ],
                            temperature=0.1,
                            max_tokens=1024,
                        )
                        current_explanation = response.choices[0].message.content
                    except Exception as e:
                        exec_details += f"\n(Correction call failed: {str(e)})"
                        break
            else:
                # Non-python code, skip compilation run checks
                exec_details = f"Compilation check bypassed for non-Python language: {lang}."
                success = True
                steps[-1]["detail"] = f"Skipped sandbox check (non-Python language: {lang}). Code assumed correct."
                break

        if success:
            steps[-1]["status"] = "success"
            steps[-1]["detail"] = f"Code verified successfully.\n\n{exec_details}"
        else:
            steps[-1]["status"] = "failed"
            steps[-1]["detail"] = f"Code failed compilation checks within {max_attempts} attempts.\n\n{exec_details}"

        return {
            "output": current_explanation,
            "steps": steps,
            "execution_result": exec_details
        }