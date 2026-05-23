import streamlit as st
from agent.core import build_agent

st.set_page_config(page_title="AI Code Debugger", page_icon="🐛", layout="wide")

st.title("🐛 AI Code Debugger Agent")
st.caption("Powered by Groq · LangChain · RAG · PyTorch")

# Sidebar
with st.sidebar:
    st.header("How to use")
    st.markdown("""
1. Paste your **buggy code** in the text area  
2. Optionally paste the **error message**  
3. Click **Debug** and let the agent work  
4. Ask follow-up questions in the chat  
""")
    st.divider()
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    with st.spinner("Loading agent..."):
        st.session_state.agent = build_agent()

# Chat history display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input area
col1, col2 = st.columns([2, 1])
with col1:
    code_input  = st.text_area("Paste your code here", height=180, placeholder="def add(a, b):\n    return a - b  # bug!")
with col2:
    error_input = st.text_area("Error message (optional)", height=90, placeholder="TypeError: ...")
    run_btn     = st.button("🔍 Debug", use_container_width=True, type="primary")

# On Debug button
if run_btn and code_input.strip():
    user_msg = f"Debug this code:\n```python\n{code_input}\n```"
    if error_input.strip():
        user_msg += f"\n\nError message:\n```\n{error_input}\n```"

    st.session_state.messages.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    with st.chat_message("assistant"):
        with st.spinner("Debugging..."):
            response = st.session_state.agent.invoke({
                "input": user_msg,
                "chat_history": []
            })
            reply = response.get("output", "No response.")
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

# Follow-up chat
if prompt := st.chat_input("Ask a follow-up question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.agent.invoke({
                "input": prompt,
                "chat_history": []
            })
            reply = response.get("output", "No response.")
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})