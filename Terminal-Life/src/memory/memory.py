from collections import defaultdict, deque
from typing import Deque, Dict, List


class CharacterMemory:
    """Per-listener bounded memory of utterances per speaker.

    Stores recent utterances for each speaker up to a capacity. Recall returns
    the most recent `limit` (default 15) entries; callers can choose a smaller limit.
    """

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

    def dump_all(self, limit_each: int = 5):
        return {k: list(dq)[-limit_each:] for k, dq in self._mem.items()}
