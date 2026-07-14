import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from agent.core import build_agent
from classifier.train import train as train_classifier
from rag.loader import load_docs_to_chromadb

app = FastAPI(title="AI Code Debugger API")

# Mount the static folder for CSS, JS and other frontend assets
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Auto-initialization check on server boot
@app.on_event("startup")
async def startup_event():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "models", "error_classifier.pth")
    db_path = os.path.join(current_dir, "chroma_db")
    
    if not os.path.exists(model_path) or not os.path.exists(db_path):
        print("[Startup] Prerequisites missing. Performing auto-initialization...")
        if not os.path.exists(model_path):
            try:
                print("[Startup] Training error classifier model...")
                train_classifier()
            except Exception as e:
                print(f"[Startup] Failed to auto-train model: {e}")
        if not os.path.exists(db_path):
            try:
                print("[Startup] Indexing RAG documents...")
                load_docs_to_chromadb()
            except Exception as e:
                print(f"[Startup] Failed to auto-index documents: {e}")
        print("[Startup] Auto-initialization completed.")
    else:
        print("[Startup] All classifier model and RAG database assets are present.")

# Models for request validation
class DebugRequest(BaseModel):
    code: str
    error: Optional[str] = ""

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]

@app.get("/")
async def get_index():
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        # Create a basic placeholder file if it doesn't exist yet
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("<h1>AI Code Debugger Frontend is loading...</h1>")
    return FileResponse(index_path)

@app.post("/api/debug")
async def debug_code(payload: DebugRequest):
    if not payload.code.strip():
        raise HTTPException(status_code=400, detail="Code snippet cannot be empty.")
    
    agent = build_agent()
    
    # Formulate user message for the agent
    user_msg = f"Debug this code:\n```python\n{payload.code}\n```"
    if payload.error and payload.error.strip():
        user_msg += f"\n\nError message:\n```\n{payload.error}\n```"
        
    try:
        result = agent.invoke({"input": user_msg})
        return {
            "status": "success",
            "output": result.get("output", "No explanation returned."),
            "steps": result.get("steps", []),
            "error_type": result.get("error_type", "unknown"),
            "execution_result": result.get("execution_result", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")

@app.post("/api/chat")
async def chat(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
    agent = build_agent()
    
    # Format history if needed
    chat_history = [{"role": msg.role, "content": msg.content} for msg in payload.history]
    
    try:
        # Invoke agent
        result = agent.invoke({
            "input": payload.message,
            "chat_history": chat_history
        })
        return {
            "status": "success",
            "output": result.get("output", "No reply returned."),
            "steps": result.get("steps", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat execution failed: {str(e)}")

# Background task worker functions
def bg_retrain():
    try:
        print("[Background] Starting classifier model training...")
        train_classifier()
        print("[Background] Classifier model training completed successfully.")
    except Exception as e:
        print(f"[Background] Classifier model training failed: {str(e)}")

def bg_reindex():
    try:
        print("[Background] Starting RAG documents reindexing...")
        load_docs_to_chromadb()
        print("[Background] RAG documents reindexing completed successfully.")
    except Exception as e:
        print(f"[Background] RAG documents reindexing failed: {str(e)}")

@app.post("/api/retrain")
async def retrain_model(background_tasks: BackgroundTasks):
    background_tasks.add_task(bg_retrain)
    return {"status": "processing", "message": "Model training has been triggered in the background."}

@app.post("/api/reindex")
async def reindex_docs(background_tasks: BackgroundTasks):
    background_tasks.add_task(bg_reindex)
    return {"status": "processing", "message": "RAG database reindexing has been triggered in the background."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
