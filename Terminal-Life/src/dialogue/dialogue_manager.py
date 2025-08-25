import random
import re
import threading
from collections import deque
from typing import Dict, List, Tuple, Optional

from src.lm_integration.client import LocalLLMClient
from src.characters.character import Character
from src.dialogue.batch_worker import DialogueBatchWorker

SYSTEM_PROMPT = (
    "You are generating a SINGLE short in-character line of dialogue for a simulation in a convenience store.\n"
    "Rules:\n- ONE concise utterance (no narration, no quotes, no stage directions)\n"
    "- Under 18 words.\n- Natural casual tone.\n- Avoid trailing conjunctions like 'and', 'but'.\n- Finish the thought with punctuation."
)

TOPICS = [
    "snack brands",
    "energy drinks",
    "weather outside",
    "local sports score",
    "late-night cravings",
    "new product display",
    "coffee aroma",
    "checkout line speed",
    "music in the background",
    "prices vs last week"
]


class DialogueManager:
    """Manages dialogue topics, threading, and asynchronous batched generation.

    Public method generate_line remains synchronous & non-blocking; it will pull a
    pre-generated line from a buffer or fall back to a quick single call / template.
    """

    def __init__(self, batch_size: int = 6, min_buffer: int = 2):
        self.client = LocalLLMClient()
        self.available = self.client.is_available()
        # mapping pair key -> last chosen topic (for diversity)
        self.pair_topic: Dict[Tuple[str, str], str] = {}
        self.topic_counts = {t: 0 for t in TOPICS}
        # conversation threads: key -> {topic, history: deque[str], last_tick: int}
        self.threads: Dict[Tuple[str, str], Dict[str, object]] = {}
        # async batching infra
        self.stop_event = threading.Event()
        self.batch_worker = DialogueBatchWorker(self.client, self.stop_event)
        self.batch_size = batch_size
        self.min_buffer = min_buffer

    # ----------------- internal utilities -----------------
    def _pair_key(self, a: Character, b: Character) -> Tuple[str, str]:
        names = sorted([a.name, b.name])
        return (names[0], names[1])

    def _thread_key(self, a: Character, b: Character) -> Tuple[str, str]:
        return self._pair_key(a, b)

    # ----------------- context & topics -----------------
    def build_context(self, speaker: Character, listener: Character, active_names: List[str]):
        recent_from_speaker = listener.memory.recall(speaker.name, limit=2)
        recent_from_listener = speaker.memory.recall(listener.name, limit=2)
        lines: List[str] = []
        key = self._pair_key(speaker, listener)
        thread = self.threads.get(key)
        if thread and thread.get('history'):
            hist = list(thread['history'])  # type: ignore[index]
            if hist:
                lines.append("Thread recent lines: " + " | ".join(hist[-4:]))
                lines.append(f"Thread topic: {thread['topic']}")
        if recent_from_speaker:
            lines.append(f"Recent {speaker.name}-> {listener.name}: " + " | ".join(recent_from_speaker))
        if recent_from_listener:
            lines.append(f"Recent {listener.name}-> {speaker.name}: " + " | ".join(recent_from_listener))
        lines.append("Present characters: " + ", ".join(sorted(active_names)))
        return "\n".join(lines)

    def _choose_topic(self, speaker: Character, listener: Character, situational: str) -> str:
        key = self._pair_key(speaker, listener)
        last = self.pair_topic.get(key)
        situ_map = {
            'shelf': ['snack brands', 'new product display', 'prices vs last week'],
            'register': ['checkout line speed', 'prices vs last week'],
            'queue': ['checkout line speed', 'energy drinks'],
            'aisles': ['late-night cravings', 'music in the background', 'coffee aroma'],
            'produce': ['prices vs last week', 'late-night cravings'],
            'coffee': ['coffee aroma', 'late-night cravings'],
            'magazine': ['local sports score', 'music in the background'],
            'drinks': ['energy drinks', 'prices vs last week'],
            'freezer': ['late-night cravings', 'prices vs last week']
        }
        bucket = 'aisles'
        if 'register' in situational:
            bucket = 'register'
        elif 'shelf' in situational:
            bucket = 'shelf'
        elif 'checkout' in situational or 'line' in situational:
            bucket = 'queue'
        elif 'produce' in situational:
            bucket = 'produce'
        elif 'coffee' in situational:
            bucket = 'coffee'
        elif 'magazine' in situational:
            bucket = 'magazine'
        elif 'drink racks' in situational:
            bucket = 'drinks'
        elif 'freezer' in situational:
            bucket = 'freezer'
        candidates = situ_map.get(bucket, TOPICS)
        weights = []
        for t in candidates:
            if t == last:
                continue
            usage = self.topic_counts.get(t, 0)
            weights.append((t, 1.0 / (1 + usage) + random.uniform(0, 0.25)))
        if not weights:
            chosen = random.choice(TOPICS)
        else:
            weights.sort(key=lambda x: x[1], reverse=True)
            chosen = weights[0][0]
        self.pair_topic[key] = chosen
        self.topic_counts[chosen] = self.topic_counts.get(chosen, 0) + 1
        return chosen

    # ----------------- threads -----------------
    def _ensure_thread(self, speaker: Character, listener: Character, topic: str, tick: int):
        key = self._thread_key(speaker, listener)
        data = self.threads.get(key)
        last_tick_val = 0
        if data is not None:
            try:
                last_tick_val = int(data.get('last_tick', 0))  # type: ignore[arg-type]
            except Exception:
                last_tick_val = 0
        if data is None or (tick - last_tick_val > 80):
            self.threads[key] = {
                'topic': topic,
                'history': deque(maxlen=8),
                'last_tick': tick
            }
        else:
            if random.random() < 0.15:
                data['topic'] = topic
            data['last_tick'] = tick
        return self.threads[key]

    def drop_threads_involving(self, name: str):
        to_del = [k for k in self.threads if name in k]
        for k in to_del:
            del self.threads[k]

    # ----------------- batching -----------------
    def _ensure_batch(self, speaker: Character, listener: Character, situational: str, tick: int):
        if not self.available:
            return
        key = self._pair_key(speaker, listener)
        if self.batch_worker.size(key) >= self.min_buffer:
            return
        topic = self._choose_topic(speaker, listener, situational)
        thread = self._ensure_thread(speaker, listener, topic, tick)
        context = self.build_context(speaker, listener, active_names=[speaker.name, listener.name])
        thread_topic = thread['topic']  # type: ignore[index]
        batch_prompt = (
            f"Characters:\n- {speaker.name}: {speaker.personality}\n- {listener.name}: {listener.personality}\n\n"
            f"Situation: {situational}\nContext:\n{context}\n\n"
            f"Ongoing thread topic: {thread_topic}\n"
            f"Generate {self.batch_size} possible next SINGLE LINES that {speaker.name} might say to {listener.name}.\n"
            "Rules:\n- Each line standalone, <=18 words.\n- No quotes or speaker labels.\n- Vary wording.\nOutput ONLY the lines, each on its own line."
        )
        self.batch_worker.enqueue(key, {
            'system': SYSTEM_PROMPT,
            'prompt': batch_prompt,
            'count': self.batch_size,
            'max_tokens': self.batch_size * 26,
            'temperature': 0.85
        })

    # ----------------- sanitization -----------------
    def _sanitize(self, text: str) -> str:
        if not text:
            return ""
        line = text.splitlines()[0].strip().strip('"').strip("'")
        while '  ' in line:
            line = line.replace('  ', ' ')
        # remove leading labels
        if ':' in line.split(' ')[0] and len(line.split(' ')[0]) <= 12:
            parts = line.split(':', 1)
            if len(parts) == 2 and parts[1].strip():
                line = parts[1].strip()
        words = line.split()
        if len(words) > 18:
            line = ' '.join(words[:18])
        if line and line[-1] not in '.?!':
            if words and words[-1].lower() in {'and', 'but', 'so', 'because', 'if'}:
                words = words[:-1]
                line = ' '.join(words)
            line = line.rstrip(',;:-')
            if line and line[-1] not in '.?!':
                line += '.'
        return line

    # ----------------- public API -----------------
    def generate_line(self, speaker: Character, listener: Character, situational: str, verbose: bool = False, retries: int = 0, tick: int = 0, active_names: Optional[List[str]] = None):
        if active_names is None:
            active_names = []
        # schedule batch fill
        self._ensure_batch(speaker, listener, situational, tick)
        key = self._pair_key(speaker, listener)
        raw = self.batch_worker.pop(key)
        if not raw and self.available:
            # light single shot
            single_prompt = f"One short line (<=18 words). No quotes. Context: {situational}. {speaker.name} to {listener.name}."
            raw = self.client.generate(SYSTEM_PROMPT, [{"role": "user", "content": single_prompt}], max_tokens=42, temperature=0.9)
        if not raw:
            raw = self.client.fallback(speaker.name, listener.name, situational)
        msg = self._sanitize(raw)
        # mitigate register repetition
        if 'register' in situational:
            parts = msg.split()
            if parts.count('register') > 1:
                msg = re.sub(r'\bregister\b', 'counter', msg, count=parts.count('register') - 1)
        else:
            msg = re.sub(r'\bregister\b', 'here', msg)
        if verbose:
            msg = f"{msg}"
        listener.memory.remember(speaker.name, msg)
        thread = self.threads.get(key)
        if thread:
            history = thread.get('history')
            if isinstance(history, deque):
                history.append(f"{speaker.name}: {msg}")
        return msg

    def shutdown(self):
        self.stop_event.set()
