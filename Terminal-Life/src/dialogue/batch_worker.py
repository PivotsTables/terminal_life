import threading
import queue
from collections import defaultdict, deque
from typing import Deque, Dict, List, Tuple, Optional, Callable


class DialogueBatchWorker:
    """Background worker that fulfills batched dialogue generation requests.

    Each request asks the LLM for N candidate single-line utterances for a *directed*
    speaker->listener pair (order matters). Lines are stored in a buffer keyed by
    (speaker, listener). The main thread polls buffers non-blockingly.
    """

    def __init__(self, client, stop_event: threading.Event):
        self.client = client
        self.stop_event = stop_event
        self.requests: "queue.Queue[Tuple[Tuple[str,str], dict]]" = queue.Queue()
        self.buffers: Dict[Tuple[str, str], Deque[str]] = defaultdict(lambda: deque())
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    # Public API ---------------------------------------------------------
    def enqueue(self, key: Tuple[str, str], payload: dict):
        """Queue a batch generation request.

        payload keys: system, prompt, count, max_tokens (optional), temperature (optional)
        """
        self.requests.put((key, payload))

    def pop(self, key: Tuple[str, str]) -> Optional[str]:
        with self.lock:
            dq = self.buffers.get(key)
            if dq:
                try:
                    return dq.popleft()
                except IndexError:
                    return None
        return None

    def size(self, key: Tuple[str, str]) -> int:
        with self.lock:
            dq = self.buffers.get(key)
            return len(dq) if dq else 0

    # Internal -----------------------------------------------------------
    def _run(self):
        while not self.stop_event.is_set():
            try:
                key, payload = self.requests.get(timeout=0.25)
            except queue.Empty:
                continue
            if self.stop_event.is_set():
                break
            system = payload.get('system')
            prompt = payload.get('prompt')
            count = int(payload.get('count', 6))
            max_tokens = int(payload.get('max_tokens', count * 28))
            temperature = float(payload.get('temperature', 0.8))
            if not self.client.is_available():
                continue
            raw = self.client.generate(system, [{"role": "user", "content": prompt}], max_tokens=max_tokens, temperature=temperature)
            if not raw:
                continue
            # Split into candidate lines
            lines = [l.strip().strip('"').strip("'") for l in raw.splitlines()]
            cleaned: List[str] = []
            for ln in lines:
                if not ln:
                    continue
                # Strip simple numbering markers
                head = ln.split(' ', 1)[0]
                if any(head.startswith(p) for p in ('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    ln = ln.split(' ', 1)[1] if ' ' in ln else ''
                ln = ln.lstrip('-').lstrip('*').strip()
                if ln:
                    cleaned.append(ln)
                if len(cleaned) >= count:
                    break
            if not cleaned:
                continue
            with self.lock:
                dq = self.buffers[key]
                for ln in cleaned:
                    dq.append(ln)
