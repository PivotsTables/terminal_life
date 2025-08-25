import random
import re
from collections import deque
from typing import Deque, Dict, List, Tuple, Optional
from src.lm_integration.client import LocalLLMClient
from src.characters.character import Character

SYSTEM_PROMPT = """You are generating a SINGLE short in-character line of dialogue for a simulation in a convenience store.\nRules:\n- ONE concise utterance (no narration, no quotes, no stage directions)\n- Under 18 words.\n- Natural casual tone.\n- Avoid trailing conjunctions like 'and', 'but'.\n- Finish the thought with punctuation."""

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
    def __init__(self):
        self.client = LocalLLMClient()
        self.available = self.client.is_available()
        # pair key -> last topic
        self.pair_topic = {}
        # topic usage counts
        self.topic_counts = {t: 0 for t in TOPICS}
        # conversation threads: key -> {topic, history: deque[str], last_tick}
        self.threads = {}

    def build_context(self, speaker: Character, listener: Character, active_names: List[str]):
        recent_from_speaker = listener.memory.recall(speaker.name, limit=2)
        recent_from_listener = speaker.memory.recall(listener.name, limit=2)
        lines: List[str] = []
        key = tuple(sorted([speaker.name, listener.name]))
        thread = self.threads.get(key)
        if thread and thread['history']:
            lines.append("Thread recent lines: " + " | ".join(list(thread['history'])[-4:]))
            lines.append(f"Thread topic: {thread['topic']}")
        if recent_from_speaker:
            lines.append(f"Recent {speaker.name}-> {listener.name}: " + " | ".join(recent_from_speaker))
        if recent_from_listener:
            lines.append(f"Recent {listener.name}-> {speaker.name}: " + " | ".join(recent_from_listener))
        lines.append("Present characters: " + ", ".join(sorted(active_names)))
        return "\n".join(lines)

    def _sanitize(self, text: str) -> str:
        if not text:
            return ""
        # Keep only first line; strip quotes/spaces
        line = text.splitlines()[0].strip().strip('"').strip("'")
        # Collapse excess whitespace
        while '  ' in line:
            line = line.replace('  ', ' ')
        # Remove leading speaker labels if model added
        lower = line.lower()
        if lower.startswith('bob:') or lower.startswith('alice:') or ':' in line.split(' ')[0]:
            parts = line.split(':', 1)
            if len(parts) == 2 and len(parts[0]) <= 12:
                line = parts[1].strip()
        # Enforce word limit
        words = line.split()
        if len(words) > 18:
            line = ' '.join(words[:18])
        # If clearly truncated (ends with comma, conjunction, or no end punctuation) add period
        if line and line[-1] not in '.?!':
            if words and words[-1].lower() in {'and','but','so','because','if'}:
                words = words[:-1]
                line = ' '.join(words)
            line = line.rstrip(',;:-')
            if line and line[-1] not in '.?!':
                line += '.'
        return line

    def _choose_topic(self, speaker: Character, listener: Character, situational: str) -> str:
        key = tuple(sorted([speaker.name, listener.name]))
        last = self.pair_topic.get(key)
        # Prefer topic aligned with situation
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
        # Remove last topic & overweight less used
        weights = []
        for t in candidates:
            if t == last:
                continue
            usage = self.topic_counts.get(t, 0)
            # inverse frequency weight + randomness
            weights.append((t, 1.0 / (1 + usage) + random.uniform(0, 0.3)))
        if not weights:
            chosen = random.choice(TOPICS)
        else:
            weights.sort(key=lambda x: x[1], reverse=True)
            chosen = weights[0][0]
        self.pair_topic[key] = chosen
        self.topic_counts[chosen] = self.topic_counts.get(chosen, 0) + 1
        return chosen

    def current_topic_stats(self, limit=5):
        items = sorted(self.topic_counts.items(), key=lambda kv: kv[1], reverse=True)
        return items[:limit]

    def _thread_key(self, a: Character, b: Character) -> Tuple[str, str]:
        names = sorted([a.name, b.name])
        return (names[0], names[1])

    def _ensure_thread(self, speaker: Character, listener: Character, topic: str, tick: int):
        key = self._thread_key(speaker, listener)
        data = self.threads.get(key)
        if data is None or (tick - data.get('last_tick', 0) > 80):  # stale -> new thread
            self.threads[key] = {
                'topic': topic,
                'history': deque(maxlen=8),
                'last_tick': tick
            }
        else:
            # maybe rotate topic if overused
            if random.random() < 0.15:
                self.threads[key]['topic'] = topic
            self.threads[key]['last_tick'] = tick
        return self.threads[key]

    def drop_threads_involving(self, name: str):
        to_del = [k for k in self.threads if name in k]
        for k in to_del:
            del self.threads[k]

    def generate_line(self, speaker: Character, listener: Character, situational: str, verbose: bool = False, retries: int = 2, tick: int = 0, active_names: Optional[List[str]] = None):
        if active_names is None:
            active_names = []
        context_active = [n for n in active_names if n not in {speaker.name, listener.name}]
        context = self.build_context(speaker, listener, active_names=[speaker.name, listener.name] + context_active)
        system = SYSTEM_PROMPT
        topic = self._choose_topic(speaker, listener, situational)
        thread = self._ensure_thread(speaker, listener, topic, tick)
        thread_topic = thread['topic']
        prompt = f"""Characters:
- {speaker.name}: {speaker.personality}
- {listener.name}: {listener.personality}

Situation: {situational}
Context:\n{context}

Ongoing conversation thread topic: {thread_topic}
If replying, you can reference earlier thread lines naturally; avoid repeating same noun phrases exactly.

Produce only what {speaker.name} says now:"""
        msg = None
        attempts = 0
        if self.available:
            while attempts <= retries and (not msg):
                raw = self.client.generate(system, [{"role":"user","content":prompt}])
                cleaned = self._sanitize(raw or "")
                if cleaned:
                    msg = cleaned
                    break
                attempts += 1
        if not msg:
            # fallback template; sanitize to enforce punctuation
            fallback = self.client.fallback(speaker.name, listener.name, situational)
            msg = self._sanitize(fallback)
        # Filter fixation on 'register'
        if 'register' in situational:
            # allow mention at most once
            parts = msg.split()
            if parts.count('register') > 1:
                msg = re.sub(r'\bregister\b', 'counter', msg, count=parts.count('register') - 1)
        else:
            # remove stray register mentions
            msg = re.sub(r'\bregister\b', 'here', msg)
        if verbose:
            msg = f"{msg}"
        listener.memory.remember(speaker.name, msg)
        # update thread history
        thread['history'].append(f"{speaker.name}: {msg}")
        return msg
