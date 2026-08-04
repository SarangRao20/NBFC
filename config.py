"""LLM Configuration with automatic fallback chain."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")

# Feature flags
# Disable usage of DTI score in decisioning when False
USE_DTI_SCORE = True


async def llm_invoke_with_retry(llm, messages, max_retries=3, base_delay=1.5):
    """Invoke LLM with exponential backoff retry for rate limits (429)."""
    for attempt in range(max_retries):
        try:
            return await llm.ainvoke(messages)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower() or "Rate limit" in err_str:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"  ⏳ Rate limited, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
            raise
    # Fallthrough should never happen, but just in case
    return await llm.ainvoke(messages)


# ── Redis LLM Cache ─────────────────────────────────────────────────────────────
def _setup_redis_cache():
    """Connect to Redis using REDIS_URL for LLM response caching."""
    try:
        import redis
        import langchain
        from langchain_community.cache import RedisCache
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            print("    No REDIS_URL found in environment; skipping Redis cache.")
            return
        # Use rediss:// scheme to enforce SSL/TLS, no need for separate ssl param
        if not redis_url.startswith('rediss://'):
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
        client = redis.Redis.from_url(redis_url, socket_connect_timeout=5)
        client.ping()
        langchain.llm_cache = RedisCache(redis_=client)
        print("   ✅ Redis LLM Cache connected (cloud)")
    except Exception as e:
        print(f"    ⚠️ Redis cache unavailable ({e.__class__.__name__}: {str(e)[:80]}), running without cache.")

_setup_redis_cache()



def get_master_llm():
    """Sales/Advisor Agent — tries Gemini → Groq → OpenRouter."""
    return _get_llm_with_fallback(temperature=0.4)


def get_extraction_llm():
    """Registration Agent — tries Groq (fast) → Gemini."""
    return _get_llm_with_fallback(temperature=0.0)


def get_vision_llm():
    """Document Agent — Gemini 2.5 Flash for multimodal OCR."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.0
    )




def _get_llm_with_fallback(temperature: float = 0.3):
    """Try multiple providers in order until one works."""
    errors = []

    # Try 1: Groq (fastest, 30 RPM limit)
    if GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                model="llama-3.1-8b-instant",
                groq_api_key=GROQ_API_KEY,
                temperature=temperature
            )
            print("   Using: Groq (llama-3.1-8b)")
            return llm
        except Exception as e:
            errors.append(f"Groq: {str(e)[:60]}")

    # Try 2: Gemini
    if GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=GEMINI_API_KEY,
                temperature=temperature
            )
            print("   Using: Gemini (1.5-flash)")
            return llm
        except Exception as e:
            errors.append(f"Gemini: {str(e)[:60]}")

    # Try 3: OpenRouter
    if OPENROUTER_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model="meta-llama/llama-3.3-70b-instruct:free",
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
                temperature=temperature
            )
            print("   Using: OpenRouter (llama-3.3-70b)")
            return llm
        except Exception as e:
            errors.append(f"OpenRouter: {str(e)[:60]}")

    # All failed — return Groq anyway (will error at call time with clear message)
    print(f"   All LLM providers failed: {errors}")
    from langchain_groq import ChatGroq
    return ChatGroq(model="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY or "missing", temperature=temperature)
