import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables (e.g., OPENAI_API_KEY for OpenRouter)
load_dotenv()

# We use OpenRouter's base URL and your key from .env
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
API_KEY = os.getenv("OPENAI_API_KEY") # Ensure this is in your .env

if not API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file (for OpenRouter access).")

# 1. Vision LLM Instance (For Document/Verification Agent)
# Recommended: Claude 3.5 Sonnet for top-tier OCR + Structured JSON capability.
def get_vision_llm():
    return ChatOpenAI(
        model="anthropic/claude-3.5-sonnet", # OpenRouter model tag
        openai_api_base=OPENROUTER_BASE,
        openai_api_key=API_KEY,
        temperature=0.0,
        max_tokens=1024
    )

# 2. Text LLM Instance (For Registration Chatbot Agent)
# Recommended: Claude 3 Haiku or GPT-4o-mini for speed and human-like chat.
def get_chat_llm():
    return ChatOpenAI(
        model="openai/gpt-4o-mini", # OpenRouter model tag
        openai_api_base=OPENROUTER_BASE,
        openai_api_key=API_KEY,
        temperature=0.3,
        max_tokens=500
    )
