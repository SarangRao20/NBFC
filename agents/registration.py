import os
import sys
# Local imports pointing backwards because it's in a subfolder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# Project Configuration
from config import get_chat_llm

class RegistrationData(BaseModel):
    """Schema to determine if initial onboarding is complete."""
    is_complete: bool = Field(description="True if both Name and Phone are confidently collected.")
    name: str | None = Field(description="The user's full name.")
    phone: str | None = Field(description="The user's 10-digit phone number.")
    intent: str | None = Field(description="The loan product they want (e.g., Personal Loan).")

class RegistrationState(TypedDict):
    """State strictly for the Registration workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    collected_name: str | None
    collected_phone: str | None
    registration_complete: bool
    
# --- Nodes ---

def chat_node(state: RegistrationState):
    """Conversational loop for the Registration Node."""
    print("--- REGISTRATION AGENT: CHATTING ---")
    llm = get_chat_llm()
    
    system_prompt = """
    You are a polite, persuasive sales executive for a major NBFC in India.
    Welcome the user, understand their loan needs, and collect their:
    1. Full Name
    2. Phone Number
    
    Rules:
    - Never ask for everything at once. Keep it conversational.
    - If you have their Name & Phone already, politely thank them, tell them your Document Verification agent will take over now, and stop asking questions.
    """
    
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = llm.invoke(messages)
    
    return {"messages": [response]}

def extraction_node(state: RegistrationState):
    """Silent node that extracts PII using Structured Outputs to decide if we route forward."""
    print("--- REGISTRATION AGENT: DATA EXTRACTION ---")
    llm = get_chat_llm()
    data_extractor = llm.with_structured_output(RegistrationData)
    
    prompt = """
    Review the conversation history. Extract the user's Full Name, Phone Number, and Intent.
    If you are highly confident you have their actual Full Name AND 10-digit Phone number, mark `is_complete` as true.
    DO NOT guess. Only extract if explicitly provided by the user.
    """
    
    # Save tokens by only sending the last 4 messages and excluding System context
    recent_history = [
        f"{'User' if isinstance(m, HumanMessage) else 'Agent'}: {m.content}" 
        for m in state["messages"][-4:] 
        if isinstance(m, HumanMessage) or isinstance(m, AIMessage)
    ]
    
    extraction: RegistrationData = data_extractor.invoke([
        {"role": "user", "content": f"{prompt}\n\nChat History:\n{chr(10).join(recent_history)}"}
    ])
    
    return {
        "collected_name": extraction.name,
        "collected_phone": extraction.phone,
        "registration_complete": extraction.is_complete
    }

# --- Routing ---

def route_registration(state: RegistrationState):
    """Router: Chat more, or end the registration phase."""
    if state.get("registration_complete"):
        return END
    return "chat"

# --- Graph Definition ---

def build_registration_agent():
    """Compiles and returns the Registration StateGraph."""
    workflow = StateGraph(RegistrationState)

    workflow.add_node("chat", chat_node)
    workflow.add_node("extract_data", extraction_node)

    workflow.add_edge(START, "chat")
    workflow.add_edge("chat", "extract_data")
    workflow.add_conditional_edges(
        "extract_data",
        route_registration,
        {
            END: END,
            "chat": "chat"
        }
    )

    return workflow.compile()

# Example hook to test just this agent:
if __name__ == "__main__":
    app = build_registration_agent()
    print("Registration Agent initialized successfully!")
