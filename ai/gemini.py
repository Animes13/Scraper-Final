# ai/gemini.py
import os
import time
from typing import Dict, Any, Optional

from google import genai
from google.genai import types


COOLDOWN_SECONDS = 90
MAX_RETRIES = 4


class GeminiPool:
    def __init__(self):
        self.keys = [
            os.getenv("GEMINI_KEY_1"),
            os.getenv("GEMINI_KEY_2"),
            os.getenv("GEMINI_KEY_3"),
            os.getenv("GEMINI_KEY_4"),
        ]
        self.keys = [k for k in self.keys if k]
        if not self.keys:
            raise RuntimeError("Nenhuma GEMINI_KEY configurada")

        self.cooldown = {k: 0 for k in self.keys}
        self.index = 0

    def _next_key(self) -> Optional[str]:
        now = time.time()
        for _ in range(len(self.keys)):
            key = self.keys[self.index]
            self.index = (self.index + 1) % len(self.keys)
            if self.cooldown[key] <= now:
                return key
        return None

    def mark_failed(self, key: str):
        self.cooldown[key] = time.time() + COOLDOWN_SECONDS


class GeminiClient:
    def __init__(self):
        self.pool = GeminiPool()

    # --------------------------------------------------
    # PROMPT BASE (ESTRUTURAL, NÃO CRIATIVO)
    # --------------------------------------------------
    def _build_prompt(self, ctx: Dict[str, Any]) -> str:
        return f"""
VocÃª Ã© um analisador de HTML para scraping.
NÃO invente dados.
NÃO crie IDs.
NÃO chute seletores.

Tarefa:
Identificar padrÃµes estruturais estÃ¡veis no HTML abaixo.

Contexto:
Anime: {ctx.get("anime")}
URL: {ctx.get("url")}
Etapa: {ctx.get("stage")}
Erro: {ctx.get("error_type")}

HTML:
{ctx.get("html")}

Responda APENAS em JSON vÃ¡lido no formato:

{{
  "type": "episode_list | selector_fix | title_mapping",
  "confidence": 0.0,
  "rules": {{
    "css": "...",
    "xpath": "...",
    "regex": "..."
  }}
}}
"""

    # --------------------------------------------------
    # CALL
    # --------------------------------------------------
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        last_error = None

        for _ in range(MAX_RETRIES):
            key = self.pool._next_key()
            if not key:
                break

            try:
                client = genai.Client(api_key=key)
                prompt = self._build_prompt(context)

                response = client.models.generate_content(
                    model="gemini-1.5-pro",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        top_p=0.9,
                        max_output_tokens=1024,
                    )
                )

                text = response.text.strip()
                return self._safe_json(text)

            except Exception as e:
                last_error = str(e)
                self.pool.mark_failed(key)

        raise RuntimeError(f"IA_FALHA: {last_error}")

    # --------------------------------------------------
    # JSON SAFE PARSE
    # --------------------------------------------------
    def _safe_json(self, text: str) -> Dict[str, Any]:
        import json
        try:
            return json.loads(text)
        except Exception:
            raise ValueError("Resposta da IA nÃ£o Ã© JSON vÃ¡lido")