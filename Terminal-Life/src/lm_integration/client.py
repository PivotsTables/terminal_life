import os
import time
import random
from typing import List, Optional, Any, Iterable

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

class LocalLLMClient:
    def __init__(self):
        self.base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
        self.model = os.getenv("LM_STUDIO_MODEL", "openai/gpt-oss-20b")
        # If OpenAI import failed, disable client
        self.enabled = OpenAI is not None
        self._client = None
        if self.enabled and OpenAI is not None:  # runtime guard
            try:
                self._client = OpenAI(base_url=self.base_url, api_key=os.getenv("LM_STUDIO_API_KEY","not-needed"))
            except Exception:
                self.enabled = False

    def is_available(self):
        return self.enabled

    def generate(self, system: str, messages: List[dict], max_tokens=60, temperature=0.8, timeout=6) -> Optional[str]:
        if not self.enabled or not self._client:
            return None
        try:
            start = time.time()
            # messages list already in simple dict form; OpenAI python SDK accepts dicts matching schema
            payload_messages: Iterable[Any] = [{"role": "system", "content": system}] + messages
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=payload_messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if time.time() - start > timeout:
                return None
            choice = resp.choices[0]
            content = getattr(choice.message, 'content', None)
            if isinstance(content, str):
                return content.strip()
            return None
        except Exception:
            return None

    def fallback(self, speaker, listener, context):
        templates = [
            f"{listener}, have you noticed {context}?",
            f"Thinking about {context} lately.",
            f"{listener}, any opinion on {context}?",
            f"I might buy something else related to {context}.",
            f"Not sure about these prices today."
        ]
        return random.choice(templates)
