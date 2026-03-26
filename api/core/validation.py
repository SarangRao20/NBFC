"""Central validation, JSON parsing, and agent output processing utilities."""

import json
import re
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class RobustJSONParser:
    """
    Robust JSON parser that handles malformed LLM outputs.
    
    Strategies:
    1. Try parsing as-is
    2. Extract from ```json code block
    3. Extract from loose {} braces
    4. Return a fallback on failure
    """
    
    @staticmethod
    def parse(text: str, fallback: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict[str, Any]], bool, str]:
        """
        Parse JSON from text with multi-strategy resilience.
        
        Returns:
            (parsed_dict, success: bool, debug_info: str)
        """
        if not text:
            return fallback or {}, False, "Empty input"
        
        debug_info = ""
        
        # Strategy 1: Try fenced ```json block
        fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced_match:
            try:
                result = json.loads(fenced_match.group(1))
                debug_info = "Parsed from ```json fence"
                return result, True, debug_info
            except json.JSONDecodeError as e:
                debug_info = f"Fenced JSON invalid: {str(e)}"
        
        # Strategy 2: Extract ALL {} blocks and prioritize by expected keys
        loose_matches = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        
        # First pass: prioritize blocks with expected data keys
        expected_keys = ["loan_amount", "loan_purpose", "tenure", "action", "decision", "fraud_score", "dti_ratio"]
        for i, match in enumerate(loose_matches):
            try:
                result = json.loads(match)
                # Check if this block has important keys
                if any(k in result for k in expected_keys):
                    debug_info = f"Parsed from loose block #{i} (has priority keys)"
                    return result, True, debug_info
            except json.JSONDecodeError:
                pass
        
        # Second pass: accept any valid JSON
        for i, match in enumerate(loose_matches):
            try:
                result = json.loads(match)
                debug_info = f"Parsed from loose block #{i}"
                return result, True, debug_info
            except json.JSONDecodeError:
                pass
        
        # Fallback
        debug_info = "All parsing strategies failed; returning fallback"
        return fallback or {}, False, debug_info
    
    @staticmethod
    def safe_extract_field(data: Dict[str, Any], key: str, default: Any = None, expected_type=None) -> Any:
        """
        Safely extract and optionally type-check a field from parsed JSON.
        
        Args:
            data: Parsed dict
            key: Field name
            default: Default value if key missing
            expected_type: Optional type to validate (e.g., float, str)
        
        Returns:
            Field value or default, with type coercion if possible
        """
        if key not in data:
            return default
        
        value = data[key]
        
        if expected_type and not isinstance(value, expected_type):
            # Try coercion
            try:
                return expected_type(value)
            except (ValueError, TypeError):
                logger.warning(f"Field '{key}' type mismatch: expected {expected_type}, got {type(value)}")
                return default
        
        return value


def validate_agent_output(agent_name: str, output: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Central validation for agent outputs.
    
    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    required_fields = {
        "document_agent": ["documents", "messages"],
        "kyc_agent": ["kyc_status"],
        "fraud_agent": ["fraud_score", "fraud_signals"],
        "underwriting_agent": ["decision", "dti_ratio"],
        "persuasion_agent": ["negotiation_round"],
        "sales_agent": ["reply"],
    }
    
    # Check if agent is known
    if agent_name not in required_fields:
        return True, None  # Unknown agent; skip validation
    
    required = required_fields[agent_name]
    missing = [f for f in required if f not in output]
    
    if missing:
        return False, f"Agent {agent_name} missing required fields: {missing}"
    
    # Type-specific validation
    try:
        if agent_name == "fraud_agent":
            score = output.get("fraud_score")
            if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                return False, f"fraud_score must be float in [0, 1], got {score}"
            
            signals = output.get("fraud_signals")
            if not isinstance(signals, int) or not (0 <= signals <= 6):
                return False, f"fraud_signals must be int in [0, 6], got {signals}"
        
        elif agent_name == "underwriting_agent":
            dti = output.get("dti_ratio")
            if dti is not None and (not isinstance(dti, (int, float)) or not (0.0 <= dti <= 10.0)):
                return False, f"dti_ratio must be fraction [0, 10], got {dti}"
            
            decision = output.get("decision", "")
            if decision and decision not in ["approve", "soft_reject", "hard_reject", "pending_docs", "reject"]:
                return False, f"decision must be in approved list, got '{decision}'"
        
        return True, None
    
    except Exception as e:
        return False, f"Validation error for {agent_name}: {str(e)}"


def extract_and_merge_agent_output(
    agent_name: str,
    raw_output: Dict[str, Any],
    current_state: Dict[str, Any],
    strict: bool = True
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Validate and merge an agent output into the current state.
    
    Args:
        agent_name: Name of agent (e.g., "fraud_agent")
        raw_output: Raw dict returned by agent node
        current_state: Current pipeline state
        strict: If True, fail on validation error; if False, log warning and continue
    
    Returns:
        (merged_state, error_or_warning: Optional[str])
    """
    # Validate
    is_valid, err = validate_agent_output(agent_name, raw_output)
    
    if not is_valid:
        msg = f"❌ Validation failed for {agent_name}: {err}"
        logger.error(msg)
        if strict:
            return current_state, msg
        else:
            logger.warning(f"Continuing despite validation error: {msg}")
    
    # Merge (all agent outputs are merged into top-level state)
    merged = {**current_state, **raw_output}
    
    warning = None
    if not is_valid and not strict:
        warning = f"⚠️ {agent_name} output validation failed; merged anyway: {err}"
    
    return merged, warning


class AgentAuditLog:
    """Central audit log for tracking agent execution and validation."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.log = []
    
    def record(self, agent_name: str, status: str, details: Optional[str] = None):
        """Record an agent execution."""
        entry = {
            "agent": agent_name,
            "status": status,  # "started", "success", "failed", "validation_error"
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.log.append(entry)
        logger.info(f"[{self.session_id}] {agent_name} → {status}" + (f": {details}" if details else ""))
    
    def get_log(self) -> list:
        """Return audit log."""
        return self.log


# Import datetime after class definition to avoid circular imports
from datetime import datetime
