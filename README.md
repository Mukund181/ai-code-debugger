# AI Code Debugger & Collaborative Learning Platform 🚀

A comprehensive, production-ready developer platform providing self-correcting debugging, educational code generation, and codebase dependency impact analysis. 

This repository is being scaled from a local single-user utility into a **distributed, collaborative multi-user enterprise platform** featuring stateful multi-agent coordination, role-based security, credit-quota failovers, and cloud containerization.

---

## 🏗️ System Architecture Overview

Below is the high-level system flow showing how the collaborative layers, stateful multi-agent orchestrator, and graceful credit failover gateway sit on top of the core parsing engine:

```mermaid
graph TD
    %% User Tier
    U1[Admin / Developer] -->|Auth / Join Session| WS[FastAPI WebSockets / API Gateway]
    U2[Member Developer] -->|Auth / Join Session| WS
    
    %% API / Orchestration Gateway
    WS -->|State Persistence| DB[(Postgres / Redis Session Store)]
    WS -->|Triggers Orchestrator| MA[Stateful Multi-Agent Orchestrator]
    
    %% Multi-Agent Router
    subgraph Multi-Agent Collaboration Hub
        MA -->|Task Routing| AR[Supervisor Router]
        AR -->|Core Code Fixes| DBG[Debugger Agent]
        AR -->|Codebase Graph Queries| RAG[Graph RAG Retriever]
        AR -->|Safety Checks| SEC[Security Auditor]
        
        DBG <-->|Verification Loop| SB[Secure Sandbox Runner]
        RAG <-->|Call Path Search| CG[(ChromaDB + Code Dependency Graph)]
    end
    
    %% Intelligent LLM Gateway
    AR -->|LLM Requests| GW[AWS Bedrock Unified API Gateway]
    
    subgraph AWS Bedrock Unified API Gateway
        GW -->|Step 1: Check Quota & Limit| P1[Premium Model: Claude 3.5 Sonnet]
        P1 -->|Fallback / Quota Exhaustion| P2[Standard Model: Meta Llama 3]
    end

    %% Deployment
    SB -->|Output Responses| WS
```

---

## 🌟 Key Features & Core Engines

### 1. ⚙️ Core Engines (Existing)
*   **🐛 Bug Debugger (Python):** Analyzes stack traces, predicts crash categories using a local PyTorch classifier, and executes a **Self-Correcting Execution Sandbox Loop** (auto-correcting code up to 3 times via subprocess checking).
*   **💡 CS Concept & Code Generator:** Creates production-ready code snippets with detailed computer science tutorials and Big-O Time/Space complexity analyses.
*   **📊 GitHub Analyzer (Graph RAG):** Downloads public repos, extracts multi-language files (Python AST, JS/TS/Java/C++/Go/Ruby regex parsing), builds a local **Code Dependency Network Graph**, and traces downstream impact breaks using BFS call path checking.

### 2. 🤖 Stateful Multi-Actor Agent System (New Plan)
Instead of executing standalone linear LLM prompts, the platform orchestrates a group of stateful sub-agents collaborating over a shared thread state:
*   **Supervisor Router Agent:** Examines user queries and delegates subtasks to specialized agents, tracking execution progress.
*   **Debugger Agent:** Analyzes run-time errors and refines correction code iteratively.
*   **Security & Sandbox Auditor:** Inspects all code snippets in the sandbox before they run, applying strict syntax verification and blocking harmful OS commands (e.g., recursive deletes, network sockets open).
*   **Graph RAG Retriever:** Explores the AST code graphs and ChromaDB embeddings to pull precise caller/callee contexts.
*   **State Management:** Thread state is serialized and persisted in a relational database (`PostgreSQL` for historical chat threads and project workspaces) and a memory cache (`Redis` for real-time connection lists, rate limiting, and ephemeral WebSocket channel states).

### 3. 👥 User Auth & Collaborative Projects (New Plan)
*   **Secure Authentication:** User signup, login, password hashing (bcrypt), and session handling via JWT (JSON Web Tokens) or OAuth2 (GitHub/Google Login).
*   **Project Workspaces:** Users can organize their debugging targets into distinct project workspaces.
*   **Project Credentials:** Each workspace has a unique `Project ID` and generated `Join Key` (e.g., `proj_sec_abcd1234`). Developers can join a shared debugging workspace collaboratively by inputting this key.
*   **Real-time Collaborative Sandbox:** Utilizes WebSockets (`/ws/project/{project_id}`) to synchronize operations:
    *   Synchronized active file views.
    *   Real-time chat with collaborative agents.
    *   Shared logs displaying live agent run steps.
    *   Live cursors showing where team members are looking in the codebase.

### 4. 🛡️ Role-Based Access Control (RBAC) (New Plan)
To support teams, access permissions are structured around clear operational boundaries:

| Permission / Action | Group Admin | Member |
| :--- | :---: | :---: |
| Run Sandbox Code & Ask Agents | Yes | Yes |
| Run Downstream Breakage Reports | Yes | Yes |
| Read Workspace Files & Code Graph | Yes | Yes |
| Manage Workspace Name & Settings | Yes | No |
| Rotate Project Access / Joining Keys | Yes | No |
| Add/Remove Team Members | Yes | No |
| Manage API Credit Quotas & Model Selects | Yes | No |
| View System Billing & API Logs | Yes | No |

### 5. 🔄 Graceful LLM Delegation & Quota Failover (New Plan)
To optimize operating costs and maintain high availability, the platform leverages **AWS Bedrock** as a unified API gateway hosting all LLM models:
1.  **Unified API Integration via AWS Bedrock:** All LLM queries are routed through AWS Bedrock as the unified API layer. This provides a single, standardized client surface to manage and switch between Anthropic Claude 3.5 Sonnet (Premium) and Meta Llama 3 (Standard).
2.  **Credit Check & Degradation Policy Middleware:** A database middleware intercepts calls to check:
    *   Has the workspace's assigned monthly credit/token quota run out?
    *   Is the primary model (Claude 3.5 Sonnet) encountering rate limits or provider downtime?
3.  **Graceful Model Failover:** If premium quotas are exceeded or limits are hit, the gateway automatically falls back to Meta Llama 3 within the same Bedrock client instance.
4.  **UI Notification:** Displays a real-time WebSocket warning back to users: *"Switched to standard model (Llama 3) via AWS Bedrock due to quota/rate limits."*

### 6. 🐳 Containerization & Hugging Face Spaces Deployment (New Plan)
*   **Multi-Stage Dockerfile:** An optimized Docker setup compiles C/C++ dependencies (if needed for AST tools), runs Python package installs, builds frontend assets, and exposes the app.
*   **Hugging Face Spaces Native Integration:**
    *   The container binds to port `7860` (as required by Hugging Face Spaces).
    *   Stores SQLite or ChromaDB indexes inside `/data` mapped as an HF Persistent Storage Volume to keep repository indices persistent across container restarts.
    *   Exposes secure credentials via Hugging Face Repository Secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, etc.).

---

## 📂 Project Directory Structure (Planned Expansion)

```
├── agent/
│   ├── core.py             # Existing DebugAgent & GenerationAgent implementation
│   ├── tools.py            # Existing Classification, doc retrieval, sandbox runner
│   └── orchestrator/       # [NEW] Multi-Agent state definitions (LangGraph / Router / Safety Auditor)
├── auth/                   # [NEW] User authentication modules
│   ├── models.py           # User and Workspace models (SQLAlchemy)
│   ├── rbac.py             # Role validation and decorator checks
│   └── routes.py           # Login, registration, token generation
├── classifier/
│   ├── model.py            # PyTorch ErrorClassifier
│   ├── predict.py          # Classifies trace inputs via embeddings
│   └── train.py            # Training routines (40+ standard exceptions)
├── db/                     # [NEW] Relational Database layer
│   ├── config.py           # Postgres / SQLite connectivity
│   └── session.py          # Session factories
├── gateway/                # [NEW] LLM Gateway & Failover
│   ├── router.py           # Intelligent Bedrock LLM Router (Claude to Llama 3)
│   └── quota.py            # Credits check and usage tracker
├── rag/
│   ├── loader.py           # Doc parser and ChromaDB indexing
│   └── embedder.py         # Embedding generation and query retrieval
├── repo_analyzer/
│   ├── ast_parser.py       # Multi-language files AST & regex parser
│   ├── graph_rag.py        # Local network dependency graph builder
│   └── routes.py           # GitHub downloader & analyzer routes
├── static/
│   ├── index.html          # Interactive Tab-based Workspace
│   ├── style.css           # Premium Light Theme stylesheet
│   └── app.js              # Event logic & Markdown code-block renderer
├── websockets/             # [NEW] Collaborative synchronization layer
│   └── manager.py          # WebSocket connection broadcaster for live collaborative debugging
├── Dockerfile              # Containerization recipe (exposes 7860, configures volumes)
├── main.py                 # FastAPI Web, WS & API Application Boot
└── requirements.txt        # Package dependencies (adding sqlalchemy, PyJWT, boto3)
```

---

## 🛠️ Setup & Execution

### 1. Prerequisites
Ensure you have Python 3.10+ and Docker installed.

Set your API keys and credentials in a `.env` file in the project root:
```env
# Core Keys
GROQ_API_KEY=gsk_...
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# AWS Bedrock Credentials (Unified API Gateway hosting Claude and Llama)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# JWT Secret
JWT_SECRET=super_secret_jwt_key
```

### 2. Local Installation
```bash
# Clone the repository
git clone https://github.com/Mukund181/ai-code-debugger.git
cd ai-code-debugger

# Install dependencies
pip install -r requirements.txt
```

### 3. Running Programmatic Tests
Validate that local PyTorch models, parsers, and agents run successfully:
```bash
python scratch_test.py
```

### 4. Running the App locally
```bash
# Launch FastAPI app
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000` to view the interface.

---

## 🐳 Containerization & Deployment

### 1. Building the Docker Container
The application can be built locally using Docker:
```bash
docker build -t ai-code-platform .
docker run -p 8000:8000 --env-file .env ai-code-platform
```

### 2. Deploying to Hugging Face Spaces

1.  **Create a New Space:** Create a Docker Space on Hugging Face Spaces.
2.  **Configure Spaces Metadata:** Add the following YAML metadata block at the top of a new Hugging Face `README.md` (or configure it in the space settings) to run properly:
    ```yaml
    title: AI Code Platform
    emoji: 🐛
    colorFrom: indigo
    colorTo: purple
    sdk: docker
    app_port: 7860
    pinned: false
    ```
3.  **Adjust Dockerfile to HF Spaces:**
    *   Expose port `7860` instead of `8000` in your Dockerfile.
    *   Add a user named `user` with uid `1000` to prevent write access permission blocks inside Hugging Face containers.
4.  **Inject Repository Secrets:** Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` in the HF Spaces secret console.
5.  **Push Code:** Push this repository to your Hugging Face Space git remote. It will automatically build the container and deploy the server.

---

## 🗺️ Platform Development Roadmap

*   [x] **Phase 1: Local Diagnostics (Core Engine)**
    *   AST parsing, classification of tracebacks, basic sandbox runner, code learning generator.
*   [ ] **Phase 2: Authentication & Collaboration Portal**
    *   JWT/OAuth user management.
    *   WebSocket server for real-time cursor/chat/file syncing in shared workspaces.
    *   Workspace credentials code generator (`proj_...`).
*   [ ] **Phase 3: Multi-Actor Orchestrator**
    *   Integration of LangGraph state router, Safety and Command Sandbox Auditor, and Graph RAG Architect agent.
*   [ ] **Phase 4: Multi-Model Gateway**
    *   AWS Bedrock unified API gateway to manage Claude and Llama 3 queries, verify credit token limits, and handle graceful degradation.
*   [ ] **Phase 5: Cloud Deployment**
    *   Multi-stage Docker builds, persistent volume configurations, and automated deploy configurations to Hugging Face Spaces.
