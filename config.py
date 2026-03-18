"""LLM Configuration with automatic fallback chain."""

import os
import time
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")


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
            # Quick test
            llm.invoke("hi")
            print("  🟢 Using: Groq (llama-3.1-8b)")
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
            llm.invoke("hi")
            print("  🟢 Using: Gemini (1.5-flash)")
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
            llm.invoke("hi")
            print("  🟢 Using: OpenRouter (llama-3.3-70b)")
            return llm
        except Exception as e:
            errors.append(f"OpenRouter: {str(e)[:60]}")

    # All failed — return Groq anyway (will error at call time with clear message)
    print(f"  ⚠️ All LLM providers failed: {errors}")
    from langchain_groq import ChatGroq
    return ChatGroq(model="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY or "missing", temperature=temperature)
