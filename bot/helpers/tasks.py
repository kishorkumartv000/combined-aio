import asyncio
import uuid
from typing import Dict, Optional

from bot.logger import LOGGER


class TaskState:
    def __init__(self, task_id: str, user_id: int, chat_id: int, label: str):
        self.task_id = task_id
        self.user_id = user_id
        self.chat_id = chat_id
        self.label = label
        self.cancel_event = asyncio.Event()
        self.subprocess: Optional[asyncio.subprocess.Process] = None
        self.status: str = "running"
        # Optional progress reporter instance
        self.progress = None


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, TaskState] = {}
        self._lock = asyncio.Lock()

    async def create(self, user: dict, label: str) -> TaskState:
        async with self._lock:
            task_id = uuid.uuid4().hex[:8]
            state = TaskState(task_id, user.get("user_id"), user.get("chat_id"), label)
            self._tasks[task_id] = state
            LOGGER.info(f"Task {task_id} created for user {state.user_id} ({label})")
            return state

    async def register_subprocess(self, task_id: str, process: asyncio.subprocess.Process):
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.subprocess = process
                LOGGER.debug(f"Task {task_id}: subprocess registered (pid={process.pid})")

    async def clear_subprocess(self, task_id: str):
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.subprocess = None

    async def attach_progress(self, task_id: str, reporter):
        """Attach a progress reporter instance to a task"""
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.progress = reporter

    async def cancel(self, task_id: str) -> bool:
        async with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return False
            if not state.cancel_event.is_set():
                state.cancel_event.set()
                state.status = "cancelling"
                if state.subprocess:
                    try:
                        state.subprocess.terminate()
                    except Exception:
                        pass
                LOGGER.info(f"Task {task_id} cancellation requested")
            return True

    async def cancel_all(self, user_id: Optional[int] = None) -> int:
        async with self._lock:
            count = 0
            for tid, state in list(self._tasks.items()):
                if user_id is not None and state.user_id != user_id:
                    continue
                if not state.cancel_event.is_set():
                    state.cancel_event.set()
                    state.status = "cancelling"
                    if state.subprocess:
                        try:
                            state.subprocess.terminate()
                        except Exception:
                            pass
                    count += 1
                    LOGGER.info(f"Task {tid} cancellation requested (bulk)")
            return count

    async def finish(self, task_id: str, status: str = "done"):
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.status = status
                # Keep a short window before deletion if needed in future
                del self._tasks[task_id]
                LOGGER.info(f"Task {task_id} finished with status={status}")

    async def get(self, task_id: str) -> Optional[TaskState]:
        # Read-only; acceptable without lock
        return self._tasks.get(task_id)

    async def list(self, user_id: Optional[int] = None) -> Dict[str, TaskState]:
        """Return current tasks, optionally filtered by user_id"""
        if user_id is None:
            return dict(self._tasks)
        return {tid: st for tid, st in self._tasks.items() if st.user_id == user_id}


# Singleton
task_manager = TaskManager()