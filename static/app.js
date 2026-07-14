document.addEventListener("DOMContentLoaded", () => {
    // Nav Tabs Elements
    const tabDebugger = document.getElementById("tab-debugger");
    const tabGenerator = document.getElementById("tab-generator");
    const tabAnalyzer = document.getElementById("tab-analyzer");
    
    const debuggerContainer = document.getElementById("debugger-container");
    const generatorContainer = document.getElementById("generator-container");
    const analyzerContainer = document.getElementById("analyzer-container");

    // Tab 1: Debugger Workspace DOM Elements
    const dbgLineNumbers = document.getElementById("dbg-line-numbers");
    const dbgCodeInput = document.getElementById("code-input");
    const dbgErrorInput = document.getElementById("error-input");
    const dbgBtnDebug = document.getElementById("btn-debug");
    const dbgChatMessages = document.getElementById("chat-messages");
    const dbgChatUserInput = document.getElementById("chat-user-input");
    const dbgBtnChatSend = document.getElementById("btn-chat-send");
    const dbgBtnClearChat = document.getElementById("btn-clear-chat");

    // Tab 2: Generator & Learning Hub DOM Elements
    const genTopic = document.getElementById("gen-topic");
    const genPromptInput = document.getElementById("gen-prompt-input");
    const genBtnGenerate = document.getElementById("btn-generate");
    const genOutputMessages = document.getElementById("gen-output-messages");
    const genBtnClear = document.getElementById("btn-clear-gen");

    // Tab 3: GitHub Analyzer DOM Elements
    const repoUrlInput = document.getElementById("repo-url-input");
    const btnAnalyzeRepo = document.getElementById("btn-analyze-repo");
    const repoMetaSummary = document.getElementById("repo-meta-summary");
    const repoFileList = document.getElementById("repo-file-list");
    const analyzerChangeInput = document.getElementById("analyzer-change-input");
    const btnCheckImpact = document.getElementById("btn-check-impact");
    const analyzerOutputMessages = document.getElementById("analyzer-output-messages");
    const btnClearAnalyzer = document.getElementById("btn-clear-analyzer");

    let chatHistory = [];
    let selectedFilePath = "";

    // --- TAB SWITCHING ---
    function switchTab(tabId) {
        tabDebugger.classList.remove("active");
        tabGenerator.classList.remove("active");
        tabAnalyzer.classList.remove("active");
        debuggerContainer.classList.remove("active");
        generatorContainer.classList.remove("active");
        analyzerContainer.classList.remove("active");

        if (tabId === "debugger") {
            tabDebugger.classList.add("active");
            debuggerContainer.classList.add("active");
        } else if (tabId === "generator") {
            tabGenerator.classList.add("active");
            generatorContainer.classList.add("active");
        } else if (tabId === "analyzer") {
            tabAnalyzer.classList.add("active");
            analyzerContainer.classList.add("active");
        }
        lucide.createIcons();
    }

    tabDebugger.addEventListener("click", () => switchTab("debugger"));
    tabGenerator.addEventListener("click", () => switchTab("generator"));
    tabAnalyzer.addEventListener("click", () => switchTab("analyzer"));

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
        
        const codeBlocks = [];
        let html = text;

        // 1. Extract multi-line code blocks, escape HTML inside them
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
            const index = codeBlocks.length;
            const escapedCode = code
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
            codeBlocks.push(`<pre><code class="language-${lang || 'none'}">${escapedCode}</code></pre>`);
            return `__CODE_BLOCK_${index}__`;
        });

        // 2. Extract inline code blocks
        html = html.replace(/`([^`\n]+)`/g, (match, code) => {
            const index = codeBlocks.length;
            const escapedCode = code
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
            codeBlocks.push(`<code>${escapedCode}</code>`);
            return `__CODE_BLOCK_${index}__`;
        });

        // 3. Escape HTML tags in remaining non-code text
        html = html
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // 4. Parse markdown headers
        html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

        // 5. Parse bold & italic
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // 6. Parse lists
        html = html.replace(/^\s*[-*]\s+(.*?)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

        // 7. Parse line breaks & paragraphs
        html = html.replace(/\n\n/g, '<p></p>');
        html = html.replace(/\n/g, '<br>');

        // 8. Re-insert formatted code blocks
        codeBlocks.forEach((block, index) => {
            html = html.replace(`__CODE_BLOCK_${index}__`, block);
        });

        return html;
    }

    // Toggle Button Loading States
    function setWorkingState(isWorking, agentType = "debugger") {
        if (isWorking) {
            if (agentType === "debugger") {
                dbgBtnDebug.disabled = true;
                dbgBtnDebug.innerHTML = `<i data-lucide="loader" class="spinning"></i> Debugging...`;
                dbgChatUserInput.disabled = true;
                dbgBtnChatSend.disabled = true;
            } else if (agentType === "generator") {
                genBtnGenerate.disabled = true;
                genBtnGenerate.innerHTML = `<i data-lucide="loader" class="spinning"></i> Generating...`;
            } else if (agentType === "analyzer-repo") {
                btnAnalyzeRepo.disabled = true;
                btnAnalyzeRepo.innerHTML = `<i data-lucide="loader" class="spinning"></i> Analyzing...`;
            } else if (agentType === "analyzer-impact") {
                btnCheckImpact.disabled = true;
                btnCheckImpact.innerHTML = `<i data-lucide="loader" class="spinning"></i> Checking...`;
            }
        } else {
            if (agentType === "debugger") {
                dbgBtnDebug.disabled = false;
                dbgBtnDebug.innerHTML = `<i data-lucide="play"></i> Start Debugging Agent`;
                dbgChatUserInput.disabled = false;
                dbgBtnChatSend.disabled = false;
            } else if (agentType === "generator") {
                genBtnGenerate.disabled = false;
                genBtnGenerate.innerHTML = `<i data-lucide="sparkles"></i> Generate Code & Learn`;
            } else if (agentType === "analyzer-repo") {
                btnAnalyzeRepo.disabled = false;
                btnAnalyzeRepo.innerHTML = `Analyze`;
            } else if (agentType === "analyzer-impact") {
                btnCheckImpact.disabled = false;
                btnCheckImpact.innerHTML = `<i data-lucide="shield-alert"></i> Check Code Impact`;
            }
        }
        lucide.createIcons();
    }

    // Append Message to Chat Panel
    function appendDebugMessage(role, text) {
        const bubble = document.createElement("div");
        bubble.className = `${role}-bubble message`;
        bubble.innerHTML = parseMarkdown(text);
        dbgChatMessages.appendChild(bubble);
        dbgChatMessages.scrollTop = dbgChatMessages.scrollHeight;
        chatHistory.push({ role: role, content: text });
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
        
        const formattedUserMsg = `Debug this Python snippet:\n\`\`\`python\n${code}\n\`\`\`${error ? `\n\nError Message:\n\`\`\`\n${error}\n\`\`\`` : ''}`;
        appendDebugMessage("user", formattedUserMsg);

        try {
            const response = await fetch("/api/debug", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: code, error: error })
            });

            const data = await response.json();

            if (data.status === "success") {
                appendDebugMessage("assistant", data.output);
            } else {
                appendDebugMessage("system", "Debugging agent failed to execute.");
            }
        } catch (err) {
            appendDebugMessage("system", `HTTP communication failed: ${err.message}`);
        } finally {
            setWorkingState(false, "debugger");
        }
    });

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

        genOutputMessages.innerHTML = `
            <div class="system-bubble message">
                <p><i data-lucide="loader" class="spinning"></i> The agent is drafting code and executing sandbox validation compiles...</p>
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
                genOutputMessages.innerHTML = "";
                const bubble = document.createElement("div");
                bubble.className = "assistant-bubble message";
                bubble.innerHTML = parseMarkdown(data.output);
                genOutputMessages.appendChild(bubble);
            } else {
                genOutputMessages.innerHTML = `
                    <div class="system-bubble message">
                        <p style="color:var(--status-failed);">Generation error occurred.</p>
                    </div>`;
            }
        } catch (err) {
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
        genOutputMessages.innerHTML = `
            <div class="system-bubble message">
                <p>Welcome! Describe what you'd like to build above and select a topic to get started.</p>
            </div>`;
        lucide.createIcons();
    });

    // --- GITHUB ANALYZER LOGIC ---
    btnAnalyzeRepo.addEventListener("click", async () => {
        const repoUrl = repoUrlInput.value.trim();
        if (!repoUrl) {
            alert("Please provide a public GitHub repository link!");
            return;
        }

        setWorkingState(true, "analyzer-repo");
        repoMetaSummary.style.display = "none";
        repoFileList.innerHTML = `<div class="empty-explorer"><i data-lucide="loader" class="spinning"></i> Scanning repository code hierarchy...</div>`;
        lucide.createIcons();

        try {
            const response = await fetch("/api/analyze-repo", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_url: repoUrl })
            });

            const data = await response.json();

            if (data.status === "success") {
                // Render stats metadata
                repoMetaSummary.style.display = "grid";
                repoMetaSummary.innerHTML = `
                    <div class="meta-stat-item">Repository: <strong>${data.repo_name}</strong></div>
                    <div class="meta-stat-item">Scanned Files: <strong>${data.statistics.files}</strong></div>
                    <div class="meta-stat-item">Call Links: <strong>${data.statistics.edges}</strong></div>
                    <div class="meta-stat-item">Classes Mapped: <strong>${data.statistics.classes || 0}</strong></div>
                    <div class="meta-stat-item">Functions Mapped: <strong>${data.statistics.functions || 0}</strong></div>
                `;

                // Render File Explorer tree selection list
                repoFileList.innerHTML = "";
                if (data.files_list && data.files_list.length > 0) {
                    data.files_list.forEach((filePath) => {
                        const fileItem = document.createElement("div");
                        fileItem.className = "explorer-item";
                        fileItem.innerHTML = `<i data-lucide="file-code"></i><span>${filePath}</span>`;
                        
                        fileItem.addEventListener("click", () => {
                            // Clear previous selection
                            document.querySelectorAll(".explorer-item").forEach(item => item.classList.remove("selected"));
                            fileItem.classList.add("selected");
                            selectedFilePath = filePath;
                            btnCheckImpact.disabled = false;
                        });

                        repoFileList.appendChild(fileItem);
                    });
                } else {
                    repoFileList.innerHTML = `<div class="empty-explorer">No source files mapped in the repository folder.</div>`;
                }
            } else {
                repoFileList.innerHTML = `<div class="empty-explorer" style="color:var(--status-failed);">Failed to map the repository index.</div>`;
            }
        } catch (err) {
            repoFileList.innerHTML = `<div class="empty-explorer" style="color:var(--status-failed);">Error: ${err.message}</div>`;
        } finally {
            setWorkingState(false, "analyzer-repo");
            lucide.createIcons();
        }
    });

    btnCheckImpact.addEventListener("click", async () => {
        const codeChange = analyzerChangeInput.value.trim();
        if (!selectedFilePath) {
            alert("Please select a target file from the explorer structure first!");
            return;
        }

        setWorkingState(true, "analyzer-impact");

        analyzerOutputMessages.innerHTML = `
            <div class="system-bubble message">
                <p><i data-lucide="loader" class="spinning"></i> Analyzing the dependency topology and querying callers from the Graph index...</p>
            </div>`;
        lucide.createIcons();

        try {
            const response = await fetch("/api/check-impact", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    file_path: selectedFilePath,
                    code_change: codeChange
                })
            });

            const data = await response.json();

            if (data.status === "success") {
                analyzerOutputMessages.innerHTML = "";
                const bubble = document.createElement("div");
                bubble.className = "assistant-bubble message";
                bubble.innerHTML = parseMarkdown(data.report);
                analyzerOutputMessages.appendChild(bubble);
            } else {
                analyzerOutputMessages.innerHTML = `
                    <div class="system-bubble message">
                        <p style="color:var(--status-failed);">Impact calculation error.</p>
                    </div>`;
            }
        } catch (err) {
            analyzerOutputMessages.innerHTML = `
                <div class="system-bubble message">
                    <p style="color:var(--status-failed);">Communication failed: ${err.message}</p>
                </div>`;
        } finally {
            setWorkingState(false, "analyzer-impact");
        }
    });

    btnClearAnalyzer.addEventListener("click", () => {
        analyzerChangeInput.value = "";
        analyzerOutputMessages.innerHTML = `
            <div class="system-bubble message">
                <p>Welcome! Specify modifications on the left to check codebase impact logs.</p>
            </div>`;
    });
});
