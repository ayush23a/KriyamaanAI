import sys
import os
from typing import Dict, Any

# Ensure the backend directory is in the python path so its absolute/relative imports resolve correctly
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from kriyaman.agents.base import BaseAgent, AgentResponse
from server.agent import agent_graph



class ResearchAgent(BaseAgent):
    """
    Adapter agent that wraps the existing LangGraph RAG and orchestration workflow.
    """
    def run(self, query: str, session_id: str, context: Dict[str, Any] = None) -> AgentResponse:
        initial_state = {
            "query": query,
            "session_id": session_id,
            "intent": "casual",
            "documents": [],
            "web_results": [],
            "final_answer": "",
            "sources": []
        }
        
        # Invoke the compiled LangGraph workflow
        result = agent_graph.invoke(initial_state)
        
        return AgentResponse(
            answer=result.get("final_answer", "No answer generated."),
            sources=result.get("sources", []),
            intent=result.get("intent", "unknown")
        )
