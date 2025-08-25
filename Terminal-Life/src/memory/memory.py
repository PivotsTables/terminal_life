from collections import defaultdict, deque
from typing import Deque, Dict, List


class CharacterMemory:
    """Per-listener memory of what each speaker said (bounded)."""

    def __init__(self, capacity_per_person: int = 100):
        self.capacity = capacity_per_person
        self._mem: Dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=self.capacity))

    def remember(self, speaker: str, utterance: str):
        self._mem[speaker].append(utterance)

    def recall(self, speaker: str, limit: int = 10) -> List[str]:
        dq = self._mem.get(speaker)
        if not dq:
            return []
        return list(dq)[-limit:]

    def dump_all(self, limit_each=5):
        return {k: list(v)[-limit_each:] for k, v in self._mem.items()}
from collections import defaultdict, deque
from typing import Deque, Dict, List

class CharacterMemory:
    def __init__(self, capacity_per_person: int = 100):
        self.capacity = capacity_per_person
        self._mem: Dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=self.capacity))

    def remember(self, speaker: str, utterance: str):
        self._mem[speaker].append(utterance)

    def recall(self, speaker: str, limit: int = 15) -> List[str]:
        dq = self._mem.get(speaker)
        if not dq:
            return []
        return list(dq)[-limit:]

    def dump_all(self, limit_each=5):
        out = {}
        for k, dq in self._mem.items():
            out[k] = list(dq)[-limit_each:]
        return out
