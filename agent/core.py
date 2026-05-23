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

        # Classify error
        error_type = ""
        if any(k in user_input.lower() for k in ["error", "exception", "traceback", "bug"]):
            try:
                error_type = classify_error.invoke(user_input)
            except Exception:
                error_type = "unknown"

        # Retrieve relevant docs
        try:
            retrieved = retrieve_docs.invoke(user_input)[:400]
        except Exception:
            retrieved = ""

        prompt = f"""You are an expert Python debugging assistant.

Error type detected: {error_type}
Relevant docs: {retrieved}

User query:
{user_input[:800]}

Provide:
1) What is wrong
2) Fixed code
3) Why it happened"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert Python debugging assistant. Be clear and concise."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1024,
        )

        output = response.choices[0].message.content

        # Execute code if asked
        if any(k in user_input.lower() for k in ["run", "execute", "test"]):
            code_blocks = re.findall(r"```python\n(.*?)```", user_input, re.DOTALL)
            if code_blocks:
                exec_result = execute_code.invoke(code_blocks[0])
                output += f"\n\n**Execution Result:**\n```\n{exec_result}\n```"

        return {"output": output}