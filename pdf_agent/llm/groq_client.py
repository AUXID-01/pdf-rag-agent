import os
from dotenv import load_dotenv
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Dict
from config import LLM_MODEL, LLM_MAX_TOKENS
from logs.logger import get_logger

load_dotenv()
log = get_logger("llm.groq_client")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
def call_llm(system_prompt: str, messages: List[Dict], max_tokens: int = LLM_MAX_TOKENS, temperature: float = 0.0) -> str:
    """
    Sends messages to Groq and returns raw text response.
    Retries up to 3 times with exponential backoff on failure.
    """
    try:
        log.info("llm_call_start", model=LLM_MODEL)
        
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not found. Check your .env file.")
        import httpx
        client = Groq(api_key=api_key, http_client=httpx.Client())
        
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]
        
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        raw_text = response.choices[0].message.content
        log.info("llm_call_complete", response_length=len(raw_text))
        return raw_text

    except Exception as e:
        log.error("llm_call_failure", error=str(e))
        raise
