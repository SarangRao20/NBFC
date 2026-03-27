"""LLM Configuration with automatic fallback chain."""

import os
import time
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")

# Feature flags
# Disable usage of DTI score in decisioning when False
USE_DTI_SCORE = False


# ── Redis LLM Cache (Memurai / Redis on Windows) ─────────────────────────────
def _setup_redis_cache():
    """Connect to local Redis/Memurai for LLM response caching. Silently skips if unavailable."""
    try:
        import redis
        import langchain
        from langchain_community.cache import RedisCache
        client = redis.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=1)
        client.ping()  # test connection
        langchain.llm_cache = RedisCache(redis_=client)
        print("   Redis LLM Cache connected (Memurai)")
    except Exception as e:
        print(f"    Redis cache unavailable ({e.__class__.__name__}: {str(e)[:40]}), running without cache.")

_setup_redis_cache()



def get_master_llm():
    """Sales/Advisor Agent — tries Gemini → Groq → OpenRouter."""
    return _get_llm_with_fallback(temperature=0.4)


def get_extraction_llm():
    """Registration Agent — tries Groq (fast) → Gemini."""
    return _get_llm_with_fallback(temperature=0.0)


def get_vision_llm():
    """Document Agent — Gemini 1.5 Flash for multimodal OCR."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.0
    )


# Static cache for LLM instances to prevent re-testing connectivity on every call
_cached_master_llm = None
_cached_extraction_llm = None

def _get_llm_with_fallback(temperature: float = 0.3):
    """Try multiple providers in order until one works."""
    # Note: Removed llm.invoke("hi") tests per performance optimization request
    errors = []

    # Try 1: Groq (fastest)
    if GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model="llama-3.1-8b-instant",
                groq_api_key=GROQ_API_KEY,
                temperature=temperature
            )
        except Exception as e:
            errors.append(f"Groq: {str(e)[:60]}")

    # Try 2: Gemini
    if GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=GEMINI_API_KEY,
                temperature=temperature
            )
        except Exception as e:
            errors.append(f"Gemini: {str(e)[:60]}")

    # Try 3: OpenRouter
    if OPENROUTER_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="meta-llama/llama-3.3-70b-instruct:free",
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
                temperature=temperature
            )
        except Exception as e:
            errors.append(f"OpenRouter: {str(e)[:60]}")

    # All failed — return Groq anyway
    from langchain_groq import ChatGroq
    return ChatGroq(model="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY or "missing", temperature=temperature)
