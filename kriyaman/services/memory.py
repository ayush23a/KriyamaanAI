import os
import shutil
from kriyaman.services.base import BaseService
from typing import Dict, Any

class MemoryService(BaseService):
    """
    Service responsible for handling session-scoped and long-term memory.
    Initially handles workspace directories for current sessions.
    """
    def __init__(self, base_upload_dir: str = "data/docs"):
        self.base_upload_dir = base_upload_dir

    def get_session_dir(self, session_id: str) -> str:
        """
        Returns the path to the session's workspace folder.
        """
        session_dir = os.path.join(self.base_upload_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def clear_session_memory(self, session_id: str) -> bool:
        """
        Clears files associated with the active session.
        """
        session_dir = os.path.join(self.base_upload_dir, session_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            return True
        return False

    # TODO: Future planned integration: Long-Term Memory
    # - Integrate persistent user context, cross-session message history, and user preferences.
    # - Store context embedding vectors in PostgreSQL or a dedicated graph-based memory layer.
    def get_long_term_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Placeholder interface for retrieving long-term persistent memory.
        """
        return {}
