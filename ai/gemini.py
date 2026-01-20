# ai/gemini.py
import os
import time
import json
import re
import asyncio
import requests
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

from putergenai import PuterClient

# --------------------------------------------------
# CONFIGURAÇÕES
# --------------------------------------------------
COOLDOWN_SECONDS = 60
MAX_RETRIES = 4

MODEL_POOL = [
    "gpt-4o",
    "gpt-5-nano",
    "deepseek-chat",
]

# --------------------------------------------------
# AUTH MANAGER (USER + PASSWORD → TOKEN)
# --------------------------------------------------
class PuterAuth:
    def __init__(self):
        self.username = os.getenv("PUTER_USERNAME")
        self.password = os.getenv("PUTER_PASSWORD")
        self.token: Optional[str] = None

        if not self.username or not self.password:
            raise RuntimeError("PUTER_USERNAME ou PUTER_PASSWORD não configurado")

    async def get_client(self) -> PuterClient:
        if self.token:
            return PuterClient(token=self.token, auto_update_models=True)

        client = PuterClient(auto_update_models=True)
        self.token = await client.login(self.username, self.password)
        return PuterClient(token=self.token, auto_update_models=True)


# --------------------------------------------------
# MODEL POOL
# --------------------------------------------------
class ModelPool:
    def __init__(self):
        self.cooldown = {m: 0 for m in MODEL_POOL}
        self.index = 0

    def next_model(self) -> Optional[str]:
        now = time.time()
        for _ in range(len(MODEL_POOL)):
            model = MODEL_POOL[self.index]
            self.index = (self.index + 1) % len(MODEL_POOL)
            if self.cooldown[model] <= now:
                return model
        return None

    def mark_failed(self, model: str):
        self.cooldown[model] = time.time() + COOLDOWN_SECONDS


# --------------------------------------------------
# CLIENTE PRINCIPAL (MANTÉM NOME GeminiClient)
# --------------------------------------------------
class GeminiClient:
    def __init__(self):
        self.pool = ModelPool()
        self.auth = PuterAuth()

    # --------------------------------------------------
    # BUILD PROMPT (INALTERADO)
    # --------------------------------------------------
    def _build_prompt(self, ctx: Dict[str, Any]) -> str:
        anime = ctx.get("anime", "").replace("“", '"').replace("”", '"').replace("\n", " ")

        if ctx.get("stage") == "title_mapping":
            return f"""
Você é um assistente especialista em AniList.
NÃO invente dados.
Retorne APENAS JSON válido.

Anime: {anime}

Formato obrigatório:

{{
  "type": "title_mapping",
  "confidence": 0.0,
  "rules": {{
    "title": "Título oficial no AniList"
  }}
}}
"""

        html = ctx.get("html", "").replace("“", '"').replace("”", '"')

        return f"""
Você é um analisador de HTML para scraping.
NÃO invente dados.
NÃO crie IDs.
NÃO chute seletores.

Contexto:
Anime: {anime}
URL: {ctx.get("url")}
Etapa: {ctx.get("stage")}
Erro: {ctx.get("error_type")}

HTML:
{html[:15000]}

Formato obrigatório:

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
    # BUSCA URL REAL DO ANILIST
    # --------------------------------------------------
    def _fetch_anilist_url(self, title: str) -> Optional[str]:
        query = quote_plus(title)
        url = f"https://anilist.co/search/anime?search={query}"

        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                return None

            match = re.search(r'https://anilist\.co/anime/\d+/[^\s"\']+', r.text)
            if match:
                return match.group(0)
        except Exception:
            return None

        return None

    # --------------------------------------------------
    # API PÚBLICA (SYNC)
    # --------------------------------------------------
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return asyncio.run(self._analyze_async(context))

    # --------------------------------------------------
    # IMPLEMENTAÇÃO ASYNC
    # --------------------------------------------------
    async def _analyze_async(self, context: Dict[str, Any]) -> Dict[str, Any]:
        last_error = None
        client = await self.auth.get_client()

        for _ in range(MAX_RETRIES):
            model = self.pool.next_model()
            if not model:
                break

            try:
                if not await client.is_model_available(model):
                    raise RuntimeError(f"Modelo indisponível: {model}")

                prompt = self._build_prompt(context)

                result = await client.ai_chat(
                    prompt=prompt,
                    options={
                        "model": model,
                        "temperature": 0.1,
                        "max_tokens": 1200,
                    },
                    strict_model=True,
                )

                text = result["response"]["result"]["message"]["content"]
                if not text:
                    raise ValueError("Resposta vazia da IA")

                data = self._safe_json(text)

                if context.get("stage") == "title_mapping":
                    title = data.get("rules", {}).get("title")
                    if title:
                        url = self._fetch_anilist_url(title)
                        if url:
                            data["rules"]["url"] = url

                return data

            except Exception as e:
                last_error = str(e)
                self.pool.mark_failed(model)

        raise RuntimeError(f"IA_FALHA: {last_error}")

    # --------------------------------------------------
    # JSON SAFE PARSE
    # --------------------------------------------------
    def _safe_json(self, text: str) -> Dict[str, Any]:
        text = text.replace("“", '"').replace("”", '"').strip()
        text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
        text = re.sub(r"```$", "", text).strip()

        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == -1:
            raise ValueError(f"Resposta IA sem JSON válido: {repr(text)}")

        try:
            return json.loads(text[start:end])
        except Exception as e:
            raise ValueError(f"JSON inválido: {e}\nRAW: {repr(text)}")