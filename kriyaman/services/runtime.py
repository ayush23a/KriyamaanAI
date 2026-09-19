from typing import Dict, Any, Optional
from kriyaman.services.base import BaseService
from kriyaman.agents.base import BaseAgent, AgentResponse
from kriyaman.agents.research import ResearchAgent

class RuntimeService(BaseService):
    """
    Service responsible for managing agent registries and orchestrating agent execution.
    """
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        # Auto-register ResearchAgent
        self.register_agent("research", ResearchAgent())

    def register_agent(self, name: str, agent: BaseAgent):
        """
        Registers a new agent instance under the given name.
        """
        self._agents[name] = agent

    def execute_agent(self, name: str, query: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Retrieves the specified agent and runs it.
        """
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' is not registered under RuntimeService.")
        return self._agents[name].run(query, session_id, context)
