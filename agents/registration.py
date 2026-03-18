import logging
import operator
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Use Gemini 1.5 Flash exclusively
from config import get_chat_llm 
try:
    from schema import RegistrationData
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State
class RegistrationState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    collected_name: str | None
    collected_phone: str | None
    registration_complete: bool

def extract_node(state: RegistrationState):
    """Smart Extraction: Plucks Name/Phone accurately."""
    messages = state.get("messages", [])
    if not messages: return state
        
    last_msg = messages[-1]
    
    # Process only if human replied
    if isinstance(last_msg, HumanMessage):
        extractor = get_chat_llm()
        
        prompt = f"""
        Extract the Name and the 10-digit Phone number from this sentence if present.
        If missing, leave blank.
        Return EXACTLY this JSON format (no markdown):
        {{"name": "...", "phone": "..."}}
        Text: '{last_msg.content}'
        """
        
        try:
             import json
             raw_reply = extractor.invoke([HumanMessage(content=prompt)]).content
             clean_json = raw_reply.replace("```json", "").replace("```", "").strip()
             data = json.loads(clean_json)
             
             updates = {}
             if data.get("name") and data["name"] != "...":
                  updates["collected_name"] = data["name"]
             if data.get("phone") and data["phone"] != "...":
                  updates["collected_phone"] = data["phone"]
                  
             return updates
             
        except Exception as e:
             logger.error(f"Extraction failed: {e}")
             
    return state

def chat_node(state: RegistrationState):
    """Conversational Node: Uses Gemini to strictly ask for what's mathematically missing."""
    name = state.get("collected_name")
    phone = state.get("collected_phone")
    
    # Check if both are collected
    if name and phone:
        # Crucial Phase Shift!
        msg = AIMessage(content="Perfect! Your profile is assembled. We are now ready for Document Verification.")
        return {"messages": [msg], "registration_complete": True}
        
    chat_llm = get_chat_llm() 
    
    system_prompt = f"""
    You are a polite NBFC Loan Assistant. 
    Your ONLY objective is to precisely collect the user's 'Full Name' and '10-digit Phone Number'.
    Do NOT ask them why they need a loan. Do NOT ask them for their profession. ONLY ask for the missing fields below.
    Currently Collected Name: {name or 'Missing'}
    Currently Collected Phone: {phone or 'Missing'}
    
    If 'Missing', gently ask the user to type it. Be extremely brief (1 sentence max).
    """
    
    chat_history = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))
    
    try:
        reply = chat_llm.invoke(chat_history)
        return {"messages": [reply]}
    except Exception as e:
        return {"messages": [AIMessage(content="Sorry! Please provide your missing details!")]}

def route_registration(state: RegistrationState):
    """Router: Waits for Streamlit Frontend gracefully."""
    return END

def build_registration_agent():
    builder = StateGraph(RegistrationState)
    builder.add_node("extract", extract_node)
    builder.add_node("chat", chat_node)
    
    builder.set_entry_point("extract")
    builder.add_edge("extract", "chat")
    builder.add_conditional_edges("chat", route_registration)
    
    return builder.compile()
