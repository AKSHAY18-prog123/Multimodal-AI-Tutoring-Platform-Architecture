from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class SessionContext:
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.active_topic: Optional[str] = None
        self.active_concept: Optional[str] = None
        self.current_learning_goal: Optional[str] = None
        self.recent_turns: List[Dict[str, str]] = [] # [{role: 'user', content: '...'}]
        self.session_start = datetime.now(timezone.utc)
        self.reading_time_seconds = 0.0
        self.answering_time_seconds = 0.0

class ShortTermMemoryManager:
    """Manages ephemeral working memory for active user chat sessions."""

    def __init__(self):
        self._sessions: Dict[str, SessionContext] = {}

    def get_or_create(self, session_id: str, user_id: str) -> SessionContext:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext(session_id, user_id)
        return self._sessions[session_id]

    def add_turn(self, session_id: str, user_id: str, role: str, content: str, topic: Optional[str] = None):
        ctx = self.get_or_create(session_id, user_id)
        ctx.recent_turns.append({"role": role, "content": content})
        if topic:
            ctx.active_topic = topic
        # Maintain sliding window of last 6 turns for prompt economy
        if len(ctx.recent_turns) > 6:
            ctx.recent_turns = ctx.recent_turns[-6:]

    def get_recent_history(self, session_id: str) -> List[Dict[str, str]]:
        if session_id in self._sessions:
            return self._sessions[session_id].recent_turns
        return []

short_term_memory = ShortTermMemoryManager()
