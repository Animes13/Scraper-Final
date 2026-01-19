# ai/gemini.py
import os
import json
import time
from google import genai
from google.genai import types


class GeminiClient:
    """
    Cliente Gemini 2.5 Flash
    - Otimizado para análise estrutural de HTML/JS
    - Uso seguro no Free Tier
    - Retorna APENAS JSON válido
    """

    def __init__(
        self,
        model="gemini-2.5-flash",
        temperature=0.2,
        max_output_tokens=2048,
        retries=2
    ):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY não definida no ambiente")

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.retries = retries

    # --------------------------------------------------
    # PROMPT BASE (CONTRATO RÍGIDO)
    # --------------------------------------------------
    def _system_prompt(self):
        return (
            "Você é um analisador técnico de HTML e JavaScript.\n"
            "Sua tarefa é identificar padrões estruturais estáveis.\n"
            "Retorne SOMENTE JSON válido.\n"
            "Não explique.\n"
            "Não use markdown.\n"
            "Não invente dados.\n"
            "Não inclua texto fora do JSON.\n"
        )

    # --------------------------------------------------
    # PROMPT POR CONTEXTO
    # --------------------------------------------------
    def _context_prompt(self, context):
        if context == "anime_list":
            return (
                "Analise esta página de lista de animes.\n"
                "Identifique os cards principais repetidos.\n"
                "Crie uma strategy com:\n"
                "- selector do card\n"
                "- selector do título\n"
                "- selector do link\n"
            )

        if context == "anime_page":
            return (
                "Analise esta página de anime.\n"
                "Identifique onde os episódios são definidos.\n"
                "Priorize dados em JavaScript.\n"
            )

        if context == "episode_page":
            return (
                "Analise esta página de episódio.\n"
                "Identifique onde está a URL criptografada do player.\n"
            )

        raise ValueError(f"Contexto desconhecido: {context}")

    # --------------------------------------------------
    # CHAMADA PRINCIPAL
    # --------------------------------------------------
    def analyze_html(self, html, context):
        prompt = (
            self._system_prompt()
            + "\n"
            + self._context_prompt(context)
            + "\nHTML:\n"
            + html[:120_000]  # proteção de tokens
        )

        last_error = None

        for _ in range(self.retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_output_tokens,
                        response_mime_type="application/json"
                    ),
                )

                data = json.loads(response.text.strip())
                if not isinstance(data, dict):
                    raise ValueError("Resposta não é um objeto JSON")

                return data

            except Exception as e:
                last_error = e
                time.sleep(1.5)

        raise RuntimeError(f"Gemini falhou: {last_error}")