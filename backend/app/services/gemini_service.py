import logging
import os
import socket
import time
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger("cloudlearn.gemini")

# Prefer IPv4 over IPv6 on Windows to prevent TLS handshake timeouts
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(*args, **kwargs):
    res = _orig_getaddrinfo(*args, **kwargs)
    ipv4 = [r for r in res if r[0] == socket.AF_INET]
    ipv6 = [r for r in res if r[0] != socket.AF_INET]
    return ipv4 + ipv6


socket.getaddrinfo = _ipv4_first_getaddrinfo

# Load .env
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
backend_env_path = os.path.join(backend_dir, ".env")
if os.path.exists(backend_env_path):
    load_dotenv(backend_env_path, override=True)
load_dotenv(override=True)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# Models to attempt in order (gracefully fallback if daily free-tier limit or 503 is hit on one model)
CANDIDATE_MODELS = [
    DEFAULT_MODEL,
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
]
MODELS_TO_TRY = list(dict.fromkeys(CANDIDATE_MODELS))

# Retry configuration
MAX_RETRIES = 1  # 1 quick retry per model before advancing to next candidate model
INITIAL_BACKOFF_SECONDS = 0.5

SYSTEM_INSTRUCTION = """
You are CloudLearn AI, an expert, encouraging, and clear personalized learning companion.
Your goal is to guide students and placement aspirants toward complete mastery.

When answering a question:
1. Provide a Core Intuition (plain-English summary, no jargon).
2. Give a Step-by-Step Explanation with a practical, real-world analogy.
3. Highlight Common Mistakes or Misconceptions students often have on this concept.
4. Conclude with a Quick Self-Check Question (with a hint) so the learner can test their comprehension.

Keep your tone positive, engaging, and easy to read with clean Markdown formatting (bullet points, bold text).
"""


class GeminiServiceUnavailableError(RuntimeError):
    """Raised when Gemini returns 503 UNAVAILABLE and retries are exhausted."""
    pass


class GeminiRateLimitError(RuntimeError):
    """Raised when Gemini returns 429 RESOURCE_EXHAUSTED and retries are exhausted."""
    pass


def get_gemini_api_key() -> str:
    """Retrieve GEMINI_API_KEY from environment or backend/.env."""
    if os.path.exists(backend_env_path):
        load_dotenv(backend_env_path, override=True)
    load_dotenv(override=True)
    return os.getenv("GEMINI_API_KEY", "").strip()


def is_gemini_configured() -> bool:
    """Check if a Gemini API key is configured."""
    key = get_gemini_api_key()
    return bool(key and len(key) > 5)


def call_gemini_robust(
    prompt: str,
    system_instruction: str = SYSTEM_INSTRUCTION,
    temperature: float = 0.7,
    max_output_tokens: int = 2048,
) -> Dict[str, str]:
    """
    Calls the Gemini API with automatic exponential backoff for 503/429
    and transparent fallback across available Flash models if quota is reached.
    Guarantees API keys are never exposed.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured in backend/.env. "
            "Please obtain a free API key from https://aistudio.google.com/ and add GEMINI_API_KEY=your_key into backend/.env."
        )

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=30000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    last_error_type = None

    for target_model in MODELS_TO_TRY:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    ),
                )
                answer_text = response.text if response and response.text else "No explanation generated."
                return {"answer": answer_text, "model": target_model}
            except Exception as e:
                error_str = str(e)
                logger.warning(f"Model {target_model} attempt {attempt} error: {error_str[:120]}")

                # Permanent client / auth errors (never retry)
                if "API_KEY_INVALID" in error_str or "invalid api key" in error_str.lower():
                    raise ValueError("The configured GEMINI_API_KEY is invalid. Please verify your key at https://aistudio.google.com/.")
                if "NOT_FOUND" in error_str or "404" in error_str:
                    logger.warning(f"Model {target_model} not found or retired, skipping to next available model.")
                    break

                # Transient 503, 504, 429, or timeout
                is_503 = "503" in error_str or "504" in error_str or "unavailable" in error_str.lower() or "high demand" in error_str.lower() or "deadline" in error_str.lower()
                is_429 = "429" in error_str or "resource_exhausted" in error_str.lower() or "rate limit" in error_str.lower()
                is_transient = is_503 or is_429 or "timeout" in error_str.lower()

                if is_transient:
                    last_error_type = 503 if is_503 else (429 if is_429 else 504)
                    if "daily" in error_str.lower() or "free_tier_requests" in error_str:
                        logger.warning(f"Daily quota reached for {target_model}. Falling back to next model...")
                        break

                    if attempt < MAX_RETRIES:
                        backoff = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                        logger.warning(f"Gemini {target_model} temporary error ({last_error_type}). Retrying in {backoff:.1f}s...")
                        time.sleep(backoff)
                        continue
                    else:
                        logger.warning(f"Model {target_model} retries exhausted, falling back to next available model...")
                        break
                break

    if last_error_type == 503:
        raise GeminiServiceUnavailableError(
            "The Gemini AI service is currently experiencing high demand. Please try again in a few moments."
        )
    elif last_error_type == 429:
        raise GeminiRateLimitError(
            "The Gemini AI rate limit was reached across available models. Please wait a few moments before trying again."
        )
    else:
        raise RuntimeError("The AI learning service encountered a temporary error. Please try again in a few moments.")


def generate_learning_explanation(question: str, topic: Optional[str] = None) -> dict:
    """
    Answers a student question with clear, structured, beginner-friendly explanations.
    """
    prompt = f"Question: {question.strip()}"
    if topic and topic.strip():
        prompt = f"Subject / Topic: {topic.strip()}\n{prompt}"

    res = call_gemini_robust(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION)
    return {
        "question": question,
        "topic": topic,
        "answer": res["answer"],
        "model": res["model"],
    }
