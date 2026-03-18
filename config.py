import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
from langchain_groq import ChatGroq

load_dotenv()

# The API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

safety_rules = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
}

# 1. Vision LLM Instance (Directly pointing to Gemini 2.5 Flash using new key)
def get_vision_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=GEMINI_API_KEY,
        safety_settings=safety_rules,
        temperature=0.0
    )

# 2. Text LLM Instance 
# Groq handles LangGraph structured extraction flawlessly with massive LLM sizes and lightning speed.
def get_chat_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile", 
        groq_api_key=GROQ_API_KEY,
        temperature=0.3
    )
