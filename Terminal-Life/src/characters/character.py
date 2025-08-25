import random
from dataclasses import dataclass, field
from typing import List, Optional
from src.engine.state import Position
from src.memory.memory import CharacterMemory

PERSONALITIES = {
    "Bob": "Helpful, calm, observant store owner. Focused on smooth checkout & customer satisfaction.",
    "Alice": "Curious, upbeat, notices little details on shelves & asks questions.",
    "Ben": "Pragmatic, brief, efficiency-minded, dislikes wasted time in line.",
    "Cara": "Chatty, friendly, often strikes up light conversations with strangers.",
    "Drew": "Sarcastic but good-natured; uses dry humor about products & prices.",
    "Eve": "Analytical, detail-oriented; compares ingredients & value meticulously.",
    "Finn": "Casual, laid-back; meanders & comments on vibe more than products.",
    "Gina": "Energetic, spontaneous; impulse buyer, quick shifts in topic."
}

@dataclass
class Character:
    name: str
    pos: Position
    is_owner: bool = False
    path: List[Position] = field(default_factory=list)
    waiting_ticks: int = 0
    memory: CharacterMemory = field(default_factory=CharacterMemory)
    personality: str = ""
    target_kind: Optional[str] = None
    active: bool = True  # False means offstage (not currently in store)
    return_tick: Optional[int] = None  # when to spawn back
    mood_score: float = 0.0  # -1..1 baseline drift
    mood_label: str = "Neutral"

    def __post_init__(self):
        if not self.personality:
            self.personality = PERSONALITIES.get(self.name, "Neutral.")

    @property
    def symbol(self):
        return self.name[0].upper()

    def set_path(self, points: List[Position], target_kind: str):
        self.path = points
        self.target_kind = target_kind

    def step(self):
        if not self.active:
            return
        if self.waiting_ticks > 0:
            self.waiting_ticks -= 1
            return
        if self.path:
            self.pos = self.path.pop(0)

    def decide_wait(self):
        self.waiting_ticks = random.randint(2, 5)

    def update_mood(self):
        """Random mild drift; conversations could hook in later."""
        drift = random.uniform(-0.05, 0.05)
        self.mood_score = max(-1.0, min(1.0, self.mood_score * 0.9 + drift))
        if self.mood_score > 0.4:
            self.mood_label = "Happy"
        elif self.mood_score > 0.1:
            self.mood_label = "Upbeat"
        elif self.mood_score < -0.4:
            self.mood_label = "Irritated"
        elif self.mood_score < -0.1:
            self.mood_label = "Flat"
        else:
            self.mood_label = "Neutral"
