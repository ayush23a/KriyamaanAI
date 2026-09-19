from abc import ABC, abstractmethod
from typing import Dict, Any, List

class AgentResponse:
    """
    Standardized response structure for all agents.
    """
    def __init__(self, answer: str, sources: List[str], intent: str, extra: Dict[str, Any] = None):
        self.answer = answer
        self.sources = sources
        self.intent = intent
        self.extra = extra or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "intent": self.intent,
            **self.extra
        }

class BaseAgent(ABC):
    """
    Abstract Base Class that all agents must implement.
    """
    @abstractmethod
    def run(self, query: str, session_id: str, context: Dict[str, Any] = None) -> AgentResponse:
        """
        Executes the agent logic for a given query and session.
        """
        pass
