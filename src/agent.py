"""
AI Core System — LangGraph Agent with persistent memory + multi-LLM routing
"""
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Router ────────────────────────────────────────────────
def get_llm(provider: str = "claude") -> BaseChatModel:
    """Multi-LLM routing: claude → gemini → ollama fallback"""
    if provider == "claude":
        return ChatAnthropic(
            model="claude-sonnet-4-5",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=2048
        )
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    elif provider == "ollama":
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "gemma3:1b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

# ── State ──────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, "conversation history"]
    provider: str
    system_prompt: str

# ── Agent Node ─────────────────────────────────────────────────
def agent_node(state: AgentState) -> AgentState:
    """Core agent node with LLM routing"""
    llm = get_llm(state.get("provider", "claude"))
    system_prompt = state.get("system_prompt", 
        "You are an AI assistant specialized in Finance, Supply Chain and Operations. "
        "You have access to persistent memory across conversations. "
        "Be concise, precise and helpful."
    )
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": state["messages"] + [response]}

# ── Router Node ────────────────────────────────────────────────
def router_node(state: AgentState) -> str:
    """Route to agent or end"""
    if state["messages"] and isinstance(state["messages"][-1], HumanMessage):
        return "agent"
    return END

# ── Build Graph ────────────────────────────────────────────────
def build_graph():
    memory = MemorySaver()
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)
    return graph.compile(checkpointer=memory)

# Singleton graph
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
