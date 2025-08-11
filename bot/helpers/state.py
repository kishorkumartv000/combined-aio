from typing import Any, Dict, Optional
import asyncio

class ConversationState:
    def __init__(self):
        self._states: Dict[int, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def start(self, user_id: int, stage: str, data: Optional[Dict[str, Any]] = None):
        async with self._lock:
            self._states[user_id] = {"stage": stage, "data": data or {}}

    def start_sync(self, user_id: int, stage: str, data: Optional[Dict[str, Any]] = None):
        self._states[user_id] = {"stage": stage, "data": data or {}}

    async def clear(self, user_id: int):
        async with self._lock:
            self._states.pop(user_id, None)

    def clear_sync(self, user_id: int):
        self._states.pop(user_id, None)

    async def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        # Read-only access without lock is fine for our use
        return self._states.get(user_id)

    def get_sync(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self._states.get(user_id)

    async def set_stage(self, user_id: int, stage: str):
        async with self._lock:
            if user_id in self._states:
                self._states[user_id]["stage"] = stage

    async def set_data(self, user_id: int, key: str, value: Any):
        async with self._lock:
            if user_id not in self._states:
                self._states[user_id] = {"stage": "", "data": {}}
            self._states[user_id].setdefault("data", {})[key] = value

    async def update(self, user_id: int, stage: Optional[str] = None, **kwargs):
        async with self._lock:
            if user_id not in self._states:
                self._states[user_id] = {"stage": stage or "", "data": {}}
            if stage is not None:
                self._states[user_id]["stage"] = stage
            if kwargs:
                self._states[user_id].setdefault("data", {}).update(kwargs)

conversation_state = ConversationState()