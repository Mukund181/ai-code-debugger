document.addEventListener("DOMContentLoaded", () => {
    // Nav Tabs Elements
    const tabDebugger = document.getElementById("tab-debugger");
    const tabGenerator = document.getElementById("tab-generator");
    const debuggerContainer = document.getElementById("debugger-container");
    const generatorContainer = document.getElementById("generator-container");

    // Common DOM Elements
    const btnReindex = document.getElementById("btn-reindex");
    const btnRetrain = document.getElementById("btn-retrain");
    const agentStatusBadge = document.getElementById("agent-status-badge");

    // Tab 1: Debugger Workspace DOM Elements
    const dbgLineNumbers = document.getElementById("dbg-line-numbers");
    const dbgCodeInput = document.getElementById("code-input");
    const dbgErrorInput = document.getElementById("error-input");
    const dbgBtnDebug = document.getElementById("btn-debug");
    const dbgTimelineSteps = document.getElementById("timeline-steps");
    const dbgChatMessages = document.getElementById("chat-messages");
    const dbgChatUserInput = document.getElementById("chat-user-input");
    const dbgBtnChatSend = document.getElementById("btn-chat-send");
    const dbgBtnClearChat = document.getElementById("btn-clear-chat");

    // Tab 2: Generator & Learning Hub DOM Elements
    const genTopic = document.getElementById("gen-topic");
    const genPromptInput = document.getElementById("gen-prompt-input");
    const genBtnGenerate = document.getElementById("btn-generate");
    const genTimelineSteps = document.getElementById("gen-timeline-steps");
    const genOutputMessages = document.getElementById("gen-output-messages");
    const genBtnClear = document.getElementById("btn-clear-gen");

    let chatHistory = [];

    // --- TAB SWITCHING WORKFLOW ---
    function switchTab(tabId) {
        if (tabId === "debugger") {
            tabDebugger.classList.add("active");
            tabGenerator.classList.remove("active");
            debuggerContainer.classList.add("active");
            generatorContainer.classList.remove("active");
        } else {
            tabDebugger.classList.remove("active");
            tabGenerator.classList.add("active");
            debuggerContainer.classList.remove("active");
            generatorContainer.classList.add("active");
        }
        lucide.createIcons();
    }

    tabDebugger.addEventListener("click", () => switchTab("debugger"));
    tabGenerator.addEventListener("click", () => switchTab("generator"));

    // --- LINE NUMBER GENERATOR ---
    function updateLineNumbers() {
        const linesCount = dbgCodeInput.value.split("\n").length;
        dbgLineNumbers.innerHTML = "";
        for (let i = 1; i <= Math.max(linesCount, 10); i++) {
            const span = document.createElement("span");
            span.textContent = i;
            dbgLineNumbers.appendChild(span);
        }
    }
    dbgCodeInput.addEventListener("input", updateLineNumbers);
    updateLineNumbers();

    // --- MARKDOWN PARSER ---
    function parseMarkdown(text) {
        if (!text) return "";
        let html = text;

        // Escape standard HTML characters for XSS prevention
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

    // Toggle Loading States
    function setWorkingState(isWorking, agentType = "debugger") {
        if (isWorking) {
            setAgentStatus("pending", "Agent Running...");
            if (agentType === "debugger") {
                dbgBtnDebug.disabled = true;
                dbgBtnDebug.innerHTML = `<i data-lucide="loader" class="spinning"></i> Working...`;
                dbgChatUserInput.disabled = true;
                dbgBtnChatSend.disabled = true;
            } else {
                genBtnGenerate.disabled = true;
                genBtnGenerate.innerHTML = `<i data-lucide="loader" class="spinning"></i> Working...`;
            }
        } else {
            setAgentStatus("idle", "Agent Idle");
            if (agentType === "debugger") {
                dbgBtnDebug.disabled = false;
                dbgBtnDebug.innerHTML = `<i data-lucide="play"></i> Start Debugging Agent`;
                dbgChatUserInput.disabled = false;
                dbgBtnChatSend.disabled = false;
            } else {
                genBtnGenerate.disabled = false;
                genBtnGenerate.innerHTML = `<i data-lucide="sparkles"></i> Generate Code & Learn`;
            }
        }
        lucide.createIcons();
    }

    // --- TIMELINE STEP RENDERING ENGINE ---
    function renderTimeline(steps, containerElement) {
        containerElement.innerHTML = "";
        if (!steps || steps.length === 0) {
            containerElement.innerHTML = `
                <div class="timeline-empty">
                    <i data-lucide="info"></i>
                    <p>No activity logged yet.</p>
                </div>`;
            lucide.createIcons();
            return;
        }

        steps.forEach((step) => {
            const stepDiv = document.createElement("div");
            stepDiv.className = `timeline-step step-state-${step.status}`;

            let iconName = "circle";
            if (step.status === "pending") iconName = "loader";
            if (step.status === "success") iconName = "check-circle-2";
            if (step.status === "failed") iconName = "x-circle";

            const isSpinner = step.status === "pending" ? "spinning" : "";

            stepDiv.innerHTML = `
                <div class="step-header">
                    <div class="step-header-left">
                        <span class="step-icon"><i data-lucide="${iconName}" class="${isSpinner}"></i></span>
                        <span class="step-title">${step.name}</span>
                    </div>
                    <span class="step-arrow"><i data-lucide="chevron-down"></i></span>
                </div>
                <div class="step-details" style="display: none;">${step.detail}</div>
            `;

            const header = stepDiv.querySelector(".step-header");
            const details = stepDiv.querySelector(".step-details");
            const arrow = stepDiv.querySelector(".step-arrow");

            header.addEventListener("click", () => {
                const isOpen = details.style.display !== "none";
                details.style.display = isOpen ? "none" : "block";
                arrow.style.transform = isOpen ? "rotate(0deg)" : "rotate(180deg)";
            });

            if (step.status === "pending" || step.status === "failed") {
                details.style.display = "block";
                arrow.style.transform = "rotate(180deg)";
            }

            containerElement.appendChild(stepDiv);
        });

        lucide.createIcons();
    }

    // --- BUG DEBUGGER LOGIC ---
    dbgBtnDebug.addEventListener("click", async () => {
        const code = dbgCodeInput.value.trim();
        const error = dbgErrorInput.value.trim();

        if (!code) {
            alert("Please paste your buggy python code first!");
            return;
        }

        setWorkingState(true, "debugger");
        
        // Append user query to chat
        const formattedUserMsg = `Debug this Python snippet:\n\`\`\`python\n${code}\n\`\`\`${error ? `\n\nError Message:\n\`\`\`\n${error}\n\`\`\`` : ''}`;
        appendDebugMessage("user", formattedUserMsg);

        // Pre-timeline steps
        renderTimeline([
            { name: "Classify Error", status: "pending", detail: "Analyzing error type..." },
            { name: "Retrieve Reference Docs", status: "pending", detail: "Searching local RAG guides..." }
        ], dbgTimelineSteps);

        try {
            const response = await fetch("/api/debug", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: code, error: error })
            });

            const data = await response.json();

            if (data.status === "success") {
                renderTimeline(data.steps, dbgTimelineSteps);
                appendDebugMessage("assistant", data.output);
                setAgentStatus("success", `Agent Idle (${data.error_type})`);
            } else {
                setAgentStatus("failed", "Agent Error");
                appendDebugMessage("system", "Debugging agent failed to execute.");
            }
        } catch (err) {
            setAgentStatus("failed", "Connection Failed");
            appendDebugMessage("system", `HTTP communication failed: ${err.message}`);
        } finally {
            setWorkingState(false, "debugger");
        }
    });

    function appendDebugMessage(role, text) {
        const bubble = document.createElement("div");
        bubble.className = `${role}-bubble message`;
        bubble.innerHTML = parseMarkdown(text);
        dbgChatMessages.appendChild(bubble);
        dbgChatMessages.scrollTop = dbgChatMessages.scrollHeight;
        chatHistory.push({ role: role, content: text });
    }

    async function sendChatFollowUp() {
        const message = dbgChatUserInput.value.trim();
        if (!message) return;

        dbgChatUserInput.value = "";
        setWorkingState(true, "debugger");
        appendDebugMessage("user", message);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    history: chatHistory.slice(0, -1)
                })
            });

            const data = await response.json();

            if (data.status === "success") {
                appendDebugMessage("assistant", data.output);
            } else {
                appendDebugMessage("system", "Failed to retrieve follow-up answer from the agent.");
            }
        } catch (err) {
            appendDebugMessage("system", `Chat failed. Connection error: ${err.message}`);
        } finally {
            setWorkingState(false, "debugger");
        }
    }

    dbgBtnChatSend.addEventListener("click", sendChatFollowUp);
    dbgChatUserInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendChatFollowUp();
    });

    dbgBtnClearChat.addEventListener("click", () => {
        chatHistory = [];
        dbgChatMessages.innerHTML = `
            <div class="system-bubble message">
                <p>Chat history cleared. Send a new debugging request or ask details about the workspace.</p>
            </div>`;
    });

    // --- CODE GENERATOR & LEARNING LOGIC ---
    genBtnGenerate.addEventListener("click", async () => {
        const prompt = genPromptInput.value.trim();
        const topic = genTopic.value;

        if (!prompt) {
            alert("Please specify a program or topic description first!");
            return;
        }

        setWorkingState(true, "generator");

        // Set up template timeline steps
        renderTimeline([
            { name: "Search Concept Database", status: "pending", detail: "Querying RAG vectors..." },
            { name: "Write Code & Learning Guide", status: "pending", detail: "Structuring explanation..." }
        ], genTimelineSteps);

        // Reset output bubble
        genOutputMessages.innerHTML = `
            <div class="system-bubble message">
                <p><i data-lucide="loader" class="spinning"></i> The agent is retrieving references, drafting code, and executing compiles to ensure correct outputs...</p>
            </div>`;
        lucide.createIcons();

        try {
            const response = await fetch("/api/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: prompt, topic: topic })
            });

            const data = await response.json();

            if (data.status === "success") {
                renderTimeline(data.steps, genTimelineSteps);
                
                // Populate result
                genOutputMessages.innerHTML = "";
                const bubble = document.createElement("div");
                bubble.className = "assistant-bubble message";
                bubble.innerHTML = parseMarkdown(data.output);
                genOutputMessages.appendChild(bubble);
            } else {
                setAgentStatus("failed", "Agent Error");
                genOutputMessages.innerHTML = `
                    <div class="system-bubble message">
                        <p style="color:var(--status-failed);">Generation error occurred.</p>
                    </div>`;
            }
        } catch (err) {
            setAgentStatus("failed", "Connection Failed");
            genOutputMessages.innerHTML = `
                <div class="system-bubble message">
                    <p style="color:var(--status-failed);">Connection failed: ${err.message}</p>
                </div>`;
        } finally {
            setWorkingState(false, "generator");
        }
    });

    genBtnClear.addEventListener("click", () => {
        genPromptInput.value = "";
        genTimelineSteps.innerHTML = `
            <div class="timeline-empty">
                <i data-lucide="info"></i>
                <p>Timeline cleared.</p>
            </div>`;
        genOutputMessages.innerHTML = `
            <div class="system-bubble message">
                <p>Welcome! Describe what you'd like to build above and select a topic to get started.</p>
            </div>`;
        lucide.createIcons();
    });

    // --- ADMIN CONTROLS TRIGGER ---
    btnReindex.addEventListener("click", async () => {
        btnReindex.disabled = true;
        const oldHtml = btnReindex.innerHTML;
        btnReindex.innerHTML = `<i data-lucide="loader" class="spinning"></i> Reindexing...`;
        lucide.createIcons();

        try {
            const res = await fetch("/api/reindex", { method: "POST" });
            const data = await res.json();
            alert("RAG index rebuilding successfully triggered in background! Check terminal/docker console logs for confirmation.");
        } catch (e) {
            alert(`Reindexing request failed: ${e.message}`);
        } finally {
            btnReindex.disabled = false;
            btnReindex.innerHTML = oldHtml;
            lucide.createIcons();
        }
    });

    btnRetrain.addEventListener("click", async () => {
        btnRetrain.disabled = true;
        const oldHtml = btnRetrain.innerHTML;
        btnRetrain.innerHTML = `<i data-lucide="loader" class="spinning"></i> Retraining...`;
        lucide.createIcons();

        try {
            const res = await fetch("/api/retrain", { method: "POST" });
            const data = await res.json();
            alert("Classifier retraining successfully triggered in background! Check terminal/docker console logs for confirmation.");
        } catch (e) {
            alert(`Model retraining request failed: ${e.message}`);
        } finally {
            btnRetrain.disabled = false;
            btnRetrain.innerHTML = oldHtml;
            lucide.createIcons();
        }
    });
});
