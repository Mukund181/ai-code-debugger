document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const codeInput = document.getElementById("code-input");
    const errorInput = document.getElementById("error-input");
    const btnDebug = document.getElementById("btn-debug");
    const btnReindex = document.getElementById("btn-reindex");
    const btnRetrain = document.getElementById("btn-retrain");
    const btnClearChat = document.getElementById("btn-clear-chat");
    const timelineSteps = document.getElementById("timeline-steps");
    const chatMessages = document.getElementById("chat-messages");
    const chatUserInput = document.getElementById("chat-user-input");
    const btnChatSend = document.getElementById("btn-chat-send");
    const agentStatusBadge = document.getElementById("agent-status-badge");
    const lineNumbers = document.querySelector(".line-numbers");

    let chatHistory = [];

    // Line numbering sync
    function updateLineNumbers() {
        const linesCount = codeInput.value.split("\n").length;
        lineNumbers.innerHTML = "";
        for (let i = 1; i <= Math.max(linesCount, 10); i++) {
            const span = document.createElement("span");
            span.textContent = i;
            lineNumbers.appendChild(span);
        }
    }
    codeInput.addEventListener("input", updateLineNumbers);
    updateLineNumbers();

    // Markdown Parser Helper
    function parseMarkdown(text) {
        if (!text) return "";
        let html = text;

        // Escape HTML tags to prevent XSS
        html = html
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Code blocks with syntax
        html = html.replace(/```python\n([\s\S]*?)```/g, '<pre><code class="language-python">$1</code></pre>');
        html = html.replace(/```python([\s\S]*?)```/g, '<pre><code class="language-python">$1</code></pre>');
        html = html.replace(/```\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        // Inline code
        html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');

        // Headers
        html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

        // Bold and Italic
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Unordered lists
        html = html.replace(/^\s*[-*]\s+(.*?)$/gm, '<li>$1</li>');
        // Wrap contiguous list items in <ul>
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

        // Newlines
        html = html.replace(/\n\n/g, '<p></p>');
        html = html.replace(/\n/g, '<br>');

        return html;
    }

    // Set Status Badge
    function setAgentStatus(status, text) {
        agentStatusBadge.className = `status-badge status-${status}`;
        agentStatusBadge.querySelector(".status-text").textContent = text;
    }

    // Toggle Buttons State
    function setWorkingState(isWorking) {
        if (isWorking) {
            btnDebug.disabled = true;
            btnDebug.innerHTML = `<i data-lucide="loader" class="spinning"></i> Working...`;
            chatUserInput.disabled = true;
            btnChatSend.disabled = true;
            lucide.createIcons();
        } else {
            btnDebug.disabled = false;
            btnDebug.innerHTML = `<i data-lucide="play"></i> Start Debugging Agent`;
            chatUserInput.disabled = false;
            btnChatSend.disabled = false;
            lucide.createIcons();
        }
    }

    // Append Message to Chat Panel
    function appendMessage(role, rawContent) {
        const bubble = document.createElement("div");
        bubble.className = `${role}-bubble message`;
        bubble.innerHTML = parseMarkdown(rawContent);
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Save to chat history for context
        chatHistory.push({ role: role, content: rawContent });
    }

    // Render Timeline Steps
    function renderTimeline(steps) {
        timelineSteps.innerHTML = "";
        if (!steps || steps.length === 0) {
            timelineSteps.innerHTML = `
                <div class="timeline-empty">
                    <i data-lucide="info"></i>
                    <p>No activity logged yet.</p>
                </div>`;
            lucide.createIcons();
            return;
        }

        steps.forEach((step, idx) => {
            const stepDiv = document.createElement("div");
            stepDiv.className = `timeline-step step-state-${step.status}`;

            // Icons mapping
            let iconName = "circle";
            if (step.status === "pending") iconName = "loader";
            if (step.status === "success") iconName = "check-circle-2";
            if (step.status === "failed") iconName = "x-circle";

            const isLoader = step.status === "pending" ? "spinning" : "";

            stepDiv.innerHTML = `
                <div class="step-header">
                    <div class="step-header-left">
                        <span class="step-icon"><i data-lucide="${iconName}" class="${isLoader}"></i></span>
                        <span class="step-title">${step.name}</span>
                    </div>
                    <span class="step-arrow"><i data-lucide="chevron-down"></i></span>
                </div>
                <div class="step-details" style="display: none;">${step.detail}</div>
            `;

            // Toggle collapsible details
            const header = stepDiv.querySelector(".step-header");
            const details = stepDiv.querySelector(".step-details");
            const arrow = stepDiv.querySelector(".step-arrow");

            header.addEventListener("click", () => {
                const isOpen = details.style.display !== "none";
                details.style.display = isOpen ? "none" : "block";
                arrow.style.transform = isOpen ? "rotate(0deg)" : "rotate(180deg)";
            });

            // Automatically open step details if it's currently active or failed
            if (step.status === "pending" || step.status === "failed") {
                details.style.display = "block";
                arrow.style.transform = "rotate(180deg)";
            }

            timelineSteps.appendChild(stepDiv);
        });

        lucide.createIcons();
    }

    // Main Action: Trigger Debugging
    btnDebug.addEventListener("click", async () => {
        const code = codeInput.value.trim();
        const error = errorInput.value.trim();

        if (!code) {
            alert("Please paste your buggy python code first!");
            return;
        }

        // Initialize state
        setWorkingState(true);
        setAgentStatus("pending", "Agent Debugging...");
        
        // Push user query to chat bubble
        appendMessage("user", `Debug this Python snippet:\n\`\`\`python\n${code}\n\`\`\`${error ? `\n\nError Message:\n\`\`\`\n${error}\n\`\`\`` : ''}`);

        // Set up mock starting timeline
        renderTimeline([
            { name: "Classify Error", status: "pending", detail: "Analyzing inputs..." },
            { name: "Retrieve Reference Docs", status: "pending", detail: "RAG lookup scheduled..." }
        ]);

        try {
            const response = await fetch("/api/debug", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: code, error: error })
            });

            const data = await response.json();

            if (data.status === "success") {
                // Populate the final steps and answers
                renderTimeline(data.steps);
                appendMessage("assistant", data.output);
                setAgentStatus("success", `Agent Idle (${data.error_type})`);
            } else {
                setAgentStatus("failed", "Agent Error");
                appendMessage("system", "The debugging agent encountered an unrecoverable failure during the execution run.");
            }
        } catch (err) {
            setAgentStatus("failed", "Connection Failed");
            appendMessage("system", `Failed to communicate with FastAPI server. Error: ${err.message}`);
        } finally {
            setWorkingState(false);
        }
    });

    // Chat Follow-up
    async function sendChatFollowUp() {
        const message = chatUserInput.value.trim();
        if (!message) return;

        chatUserInput.value = "";
        setWorkingState(true);
        setAgentStatus("pending", "Agent Thinking...");
        
        appendMessage("user", message);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    history: chatHistory.slice(0, -1) // Excluding the user message we just appended
                })
            });

            const data = await response.json();

            if (data.status === "success") {
                appendMessage("assistant", data.output);
                setAgentStatus("success", "Agent Idle");
            } else {
                setAgentStatus("failed", "Agent Error");
                appendMessage("system", "Failed to retrieve follow-up answer from the agent.");
            }
        } catch (err) {
            setAgentStatus("failed", "Connection Failed");
            appendMessage("system", `Failed to retrieve chat reply. Error: ${err.message}`);
        } finally {
            setWorkingState(false);
        }
    }

    btnChatSend.addEventListener("click", sendChatFollowUp);
    chatUserInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            sendChatFollowUp();
        }
    });

    // Reindex RAG Trigger
    btnReindex.addEventListener("click", async () => {
        btnReindex.disabled = true;
        const originalText = btnReindex.innerHTML;
        btnReindex.innerHTML = `<i data-lucide="loader" class="spinning"></i> Indexing...`;
        lucide.createIcons();

        try {
            const response = await fetch("/api/reindex", { method: "POST" });
            const data = await response.json();
            alert("RAG index rebuilding successfully triggered in background! Check console output for completion status.");
        } catch (err) {
            alert(`Failed to trigger RAG indexing: ${err.message}`);
        } finally {
            btnReindex.disabled = false;
            btnReindex.innerHTML = originalText;
            lucide.createIcons();
        }
    });

    // Retrain Model Trigger
    btnRetrain.addEventListener("click", async () => {
        btnRetrain.disabled = true;
        const originalText = btnRetrain.innerHTML;
        btnRetrain.innerHTML = `<i data-lucide="loader" class="spinning"></i> Training...`;
        lucide.createIcons();

        try {
            const response = await fetch("/api/retrain", { method: "POST" });
            const data = await response.json();
            alert("Neural network classifier retraining successfully triggered in background! Check console output for completion status.");
        } catch (err) {
            alert(`Failed to trigger model training: ${err.message}`);
        } finally {
            btnRetrain.disabled = false;
            btnRetrain.innerHTML = originalText;
            lucide.createIcons();
        }
    });

    // Clear Chat History
    btnClearChat.addEventListener("click", () => {
        chatHistory = [];
        chatMessages.innerHTML = `
            <div class="system-bubble message">
                <p>Chat history cleared. Send a new debugging request or ask details about the workspace.</p>
            </div>`;
    });
});
