import asyncio
import uuid
from typing import Dict, Optional, List, Callable, Any, Tuple

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
        # Simple per-bot FIFO queue with metadata and cancel support
        self._pending: List[Dict[str, Any]] = []  # each: {qid, user_id, link, options, job}
        self._pending_event = asyncio.Event()
        self._worker_started = False

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

    # --- Queue support ---
    async def start_worker(self):
        if self._worker_started:
            return
        self._worker_started = True

        async def _worker_loop():
            while True:
                await self._pending_event.wait()
                item = None
                async with self._lock:
                    if self._pending:
                        item = self._pending.pop(0)
                    if not self._pending:
                        self._pending_event.clear()
                if not item:
                    continue
                job = item.get('job')
                try:
                    await job()
                except Exception as e:
                    try:
                        LOGGER.error(f"Queue job failed: {e}")
                    except Exception:
                        pass

        asyncio.get_event_loop().create_task(_worker_loop())

    async def enqueue(self, user_id: int, link: str, options: Dict[str, Any], job_coro_factory: Callable[[], Any]) -> Tuple[str, int]:
        """Enqueue a job with metadata, return (queue_id, position)."""
        async with self._lock:
            qid = uuid.uuid4().hex[:8]
            self._pending.append({
                'qid': qid,
                'user_id': user_id,
                'link': link,
                'options': options or {},
                'job': job_coro_factory,
            })
            self._pending_event.set()
            position = len(self._pending)
            return qid, position

    async def queue_size(self, user_id: Optional[int] = None) -> int:
        async with self._lock:
            if user_id is None:
                return len(self._pending)
            return sum(1 for it in self._pending if it.get('user_id') == user_id)

    async def list_pending(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        async with self._lock:
            items = list(self._pending)
        if user_id is not None:
            items = [it for it in items if it.get('user_id') == user_id]
        # annotate position
        for idx, it in enumerate(items, start=1):
            it['position'] = idx
        return items

    async def cancel_pending(self, qid: str, user_id: Optional[int] = None) -> bool:
        async with self._lock:
            for i, it in enumerate(self._pending):
                if it.get('qid') == qid and (user_id is None or it.get('user_id') == user_id):
                    del self._pending[i]
                    if not self._pending:
                        self._pending_event.clear()
                    return True
        return False


# Singleton
task_manager = TaskManager()