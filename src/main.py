"""
AI Core System — FastAPI server
Exposes LangGraph agent via REST API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
from src.agent import get_graph
from langchain_core.messages import HumanMessage

app = FastAPI(
    title="AI Core System",
    description="AI OS: LangGraph + multi-LLM routing + persistent memory",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    provider: Optional[str] = "claude"
    system_prompt: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    provider: str

# ── Endpoints ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "name": "AI Core System",
        "version": "1.0.0",
        "status": "running",
        "providers": ["claude", "gemini", "ollama"]
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        graph = get_graph()
        thread_id = req.thread_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        state = {
            "messages": [HumanMessage(content=req.message)],
            "provider": req.provider or "claude",
        }
        if req.system_prompt:
            state["system_prompt"] = req.system_prompt

        result = graph.invoke(state, config=config)
        last_message = result["messages"][-1]

        return ChatResponse(
            response=last_message.content,
            thread_id=thread_id,
            provider=req.provider or "claude"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/threads/{thread_id}/history")
def get_history(thread_id: str):
    """Get conversation history for a thread"""
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)
        if not state or not state.values:
            return {"thread_id": thread_id, "messages": []}
        messages = []
        for msg in state.values.get("messages", []):
            messages.append({
                "role": "human" if isinstance(msg, HumanMessage) else "assistant",
                "content": msg.content
            })
        return {"thread_id": thread_id, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
