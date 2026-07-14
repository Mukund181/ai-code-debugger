import os
import zipfile
import urllib.request
import tempfile
import shutil
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from groq import Groq
from repo_analyzer.graph_rag import CodeGraph

router = APIRouter(prefix="/api")

# In-memory session tracking for active repository paths
_current_repo_graph = CodeGraph()
_current_repo_name = ""

class AnalyzeRepoRequest(BaseModel):
    repo_url: str  # e.g., https://github.com/Mukund181/ai-code-debugger

class CheckImpactRequest(BaseModel):
    file_path: str   # Relative file path inside the repo, e.g. "agent/tools.py"
    code_change: str # Code snippet representing changes/modifications

def download_and_extract_repo(repo_url: str, extract_to: str) -> str:
    """Downloads a GitHub repository as a ZIP archive and extracts it."""
    # Convert github URL to zip link: https://github.com/user/repo -> https://github.com/user/repo/archive/refs/heads/main.zip
    clean_url = repo_url.rstrip("/")
    if "github.com" not in clean_url:
        raise ValueError("Only standard public GitHub repositories are supported currently.")
    
    # Assume main branch as default first, fallback to master
    zip_url = f"{clean_url}/archive/refs/heads/main.zip"
    zip_path = os.path.join(extract_to, "repo.zip")

    try:
        # User-Agent header is set to bypass simple blocking
        req = urllib.request.Request(
            zip_url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
    except Exception:
        # Fallback to master branch
        zip_url = f"{clean_url}/archive/refs/heads/master.zip"
        try:
            req = urllib.request.Request(
                zip_url, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch zip archive from github (tried main and master branches): {str(e)}")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    # Get the extracted directory (usually repo-name-main or repo-name-master)
    dirs = [d for d in os.listdir(extract_to) if os.path.isdir(os.path.join(extract_to, d)) and d != "__pycache__"]
    if not dirs:
        raise RuntimeError("No files found inside the extracted archive.")
    
    return os.path.join(extract_to, dirs[0])

@router.post("/analyze-repo")
async def analyze_repo(payload: AnalyzeRepoRequest):
    global _current_repo_name
    if not payload.repo_url.strip():
        raise HTTPException(status_code=400, detail="Repository URL is required.")

    temp_dir = tempfile.mkdtemp()
    try:
        print(f"[Repo Analyzer] Downloading and extracting: {payload.repo_url}...")
        extracted_path = download_and_extract_repo(payload.repo_url, temp_dir)
        
        print("[Repo Analyzer] Parsing files and building structural graph...")
        _current_repo_graph.build_from_directory(extracted_path)
        
        # Save index locally in chroma_db folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        index_dir = os.path.join(root_dir, "chroma_db")
        os.makedirs(index_dir, exist_ok=True)
        _current_repo_graph.save_index(os.path.join(index_dir, "repo_graph.json"))

        # Compute metadata counts
        nodes_count = len(_current_repo_graph.nodes)
        edges_count = len(_current_repo_graph.edges)
        files_list = sorted([
            props["name"] for n, props in _current_repo_graph.nodes.items()
            if props["type"] == "file"
        ])
        files_count = len(files_list)
        funcs_count = len([n for n, p in _current_repo_graph.nodes.items() if p["type"] in ["function", "method"]])

        _current_repo_name = payload.repo_url.split("/")[-1]

        return {
            "status": "success",
            "repo_name": _current_repo_name,
            "statistics": {
                "files": files_count,
                "nodes": nodes_count,
                "edges": edges_count,
                "functions": funcs_count
            },
            "files_list": files_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze repository: {str(e)}")
    finally:
        # Clean up temp folder files
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.post("/check-impact")
async def check_impact(payload: CheckImpactRequest):
    if not payload.file_path.strip():
        raise HTTPException(status_code=400, detail="Target file path is required.")

    # Load graph index if empty in session
    if not _current_repo_graph.nodes:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        index_path = os.path.join(root_dir, "chroma_db", "repo_graph.json")
        if not os.path.exists(index_path):
            raise HTTPException(
                status_code=400, 
                detail="No repository graph index found. Please hit /api/analyze-repo first."
            )
        _current_repo_graph.load_index(index_path)

    # Perform impact traversal query
    impact = _current_repo_graph.query_impact(payload.file_path)
    impact_chain = impact.get("impact_chain", [])

    # Format downstream context
    downstream_details = []
    for item in impact_chain:
        node_id = item["node_id"]
        node_props = _current_repo_graph.nodes.get(node_id, {})
        code_context = node_props.get("code", "")
        # Limit context chunk size to avoid token limit overflow
        if len(code_context) > 400:
            code_context = code_context[:400] + "\n... (truncated)"
        
        downstream_details.append(
            f"- Entity: {item['type']} '{item['name']}' in file '{item['file']}' (Depth: {item['depth']})\n"
            f"  Code Reference:\n```python\n{code_context}\n```"
        )

    downstream_formatted = "\n\n".join(downstream_details) if downstream_details else "No direct downstream callers found."

    # Ask LLM to run impact analysis
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    system_prompt = (
        "You are an expert software architect and dependency impact analyzer. "
        "Review proposed modifications to a file and explain what could break downstream "
        "based on the call graph relationships provided."
    )
    
    user_prompt = f"""Target File to modify: {payload.file_path}

Proposed Code Change:
```python
{payload.code_change}
```

Below is the Graph RAG retrieved downstream context (modules, functions, and methods that depend on/call elements in {payload.file_path}):
{downstream_formatted}

Please analyze this setup and provide a report on:
1) Potential breakages (signature mismatches, type conflicts, logic updates needed).
2) Safe migration strategy (steps to safely introduce the change without crashing callers).
3) General review comments.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        report = response.choices[0].message.content
        return {
            "status": "success",
            "impact_graph": impact,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Impact analysis failed: {str(e)}")
