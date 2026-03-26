"""
Comparison Service Layer — Business logic for loans API.
Bridges API layer with comparison_engine.
"""

from typing import Dict, List, Any, Optional
from agents.comparison_engine import LoanComparisonEngine
from mock_apis.lender_apis import _load_lenders_data
import json


class ComparisonService:
    """Service layer for loan comparison operations."""
    
    @staticmethod
    def get_loan_comparisons(
        loan_amount: float,
        tenure_months: int,
        credit_score: int,
        monthly_salary: float,
        age: int = 35,
        existing_obligations: float = 0
    ) -> Dict[str, Any]:
        """
        Get loan comparisons from all lenders.
        
        Args:
            loan_amount: Loan amount in INR
            tenure_months: Tenure in months
            credit_score: Credit score (600-900)
            monthly_salary: Monthly salary in INR
            age: Age in years
            existing_obligations: Monthly EMI of other loans
        
        Returns:
            Dictionary with:
            - status: 'success' or 'no_eligible_offers'
            - eligible_count: Number of eligible offers
            - ineligible_count: Number of ineligible offers
            - eligible_offers: List of eligible loan options
            - best_offer: Best recommendation
            - alternatives: Top 2 alternatives
            - recommendation_reason: Explanation
            - smart_suggestions: Suggestions if ineligible
            - applied_weights: Weight factors used
        """
        # Initialize comparison engine
        engine = LoanComparisonEngine()
        
        # Run comparison
        result = engine.compare_loans(
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            credit_score=credit_score,
            monthly_salary=monthly_salary,
            age=age,
            existing_obligations=existing_obligations
        )
        
        # Transform result to API format
        eligible_offers = []
        if result["eligible_offers"]:
            for offer in result["eligible_offers"]:
                eligible_offers.append({
                    "lender_id": offer["lender_id"],
                    "lender_name": offer["lender_name"],
                    "lender_type": offer["lender_type"],
                    "interest_rate": round(offer["interest_rate"], 2),
                    "emi": round(offer["emi"], 2),
                    "total_cost": round(offer["total_cost"], 2),
                    "approval_probability": round(offer["approval_probability"], 3),
                    "approval_percentage": round(offer["approval_probability"] * 100, 1),
                    "composite_score": round(offer["composite_score"], 2),
                    "rank_badge": offer["rank_badge"],
                    "recommendation_rank": offer["recommendation_rank"]
                })
        
        # Best offer
        best_offer = None
        if result["best_offer"]:
            offer = result["best_offer"]
            best_offer = {
                "lender_id": offer["lender_id"],
                "lender_name": offer["lender_name"],
                "lender_type": offer["lender_type"],
                "interest_rate": round(offer["interest_rate"], 2),
                "emi": round(offer["emi"], 2),
                "total_cost": round(offer["total_cost"], 2),
                "approval_probability": round(offer["approval_probability"], 3),
                "approval_percentage": round(offer["approval_probability"] * 100, 1),
                "composite_score": round(offer["composite_score"], 2),
                "rank_badge": offer["rank_badge"],
                "recommendation_rank": offer["recommendation_rank"]
            }
        
        # Alternatives
        alternatives = []
        if result["alternatives"]:
            for offer in result["alternatives"]:
                alternatives.append({
                    "lender_id": offer["lender_id"],
                    "lender_name": offer["lender_name"],
                    "lender_type": offer["lender_type"],
                    "interest_rate": round(offer["interest_rate"], 2),
                    "emi": round(offer["emi"], 2),
                    "total_cost": round(offer["total_cost"], 2),
                    "approval_probability": round(offer["approval_probability"], 3),
                    "approval_percentage": round(offer["approval_probability"] * 100, 1),
                    "composite_score": round(offer["composite_score"], 2),
                    "rank_badge": offer["rank_badge"],
                    "recommendation_rank": offer["recommendation_rank"]
                })
        
        return {
            "status": result["status"],
            "eligible_count": result["eligible_count"],
            "ineligible_count": result["ineligible_count"],
            "eligible_offers": eligible_offers,
            "best_offer": best_offer,
            "alternatives": alternatives,
            "recommendation_reason": result["recommendation_reason"],
            "smart_suggestions": result["smart_suggestions"],
            "applied_weights": result["applied_weights"]
        }
    
    @staticmethod
    def process_loan_selection(
        selected_lender_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user's loan selection.
        
        Args:
            selected_lender_id: ID of selected lender
            session_id: Optional session ID for tracking
        
        Returns:
            Dictionary with:
            - success: bool
            - message: Confirmation message
            - selected_lender: Lender name
            - selected_interest_rate: Interest rate
            - selected_emi: EMI
            - next_step: Next step in workflow (e.g., 'underwriting')
        """
        # Validate lender ID
        valid_lenders = {
            "bank_a": {"name": "Bank A", "rate": 9.5},
            "bank_b": {"name": "Bank B", "rate": 11.0},
            "nbfc_x": {"name": "NBFC X", "rate": 13.5},
            "fintech_y": {"name": "Fintech Y", "rate": 12.0},
            "credit_union_z": {"name": "Credit Union Z", "rate": 10.5}
        }
        
        if selected_lender_id.lower() not in valid_lenders:
            raise ValueError(f"Invalid lender ID: {selected_lender_id}")
        
        lender_info = valid_lenders[selected_lender_id.lower()]
        
        return {
            "success": True,
            "message": f"Loan from {lender_info['name']} selected successfully",
            "selected_lender": lender_info["name"],
            "selected_interest_rate": lender_info["rate"],
            "selected_emi": 0,  # Will be calculated based on previous comparison
            "next_step": "underwriting"
        }
    
    @staticmethod
    def run_what_if_simulation(
        session_id: str,
        new_loan_amount: Optional[float] = None,
        new_tenure_months: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run what-if simulation with new parameters.
        
        Args:
            session_id: Session ID from previous comparison
            new_loan_amount: New loan amount to simulate
            new_tenure_months: New tenure to simulate
        
        Returns:
            Dictionary with original, simulated, and differences
        """
        # TODO: Implement session storage and retrieval
        # For now, return placeholder
        return {
            "original": {
                "loan_amount": 500000,
                "tenure_months": 60,
                "emi": 10000,
                "best_rate": 9.5
            },
            "simulated": {
                "loan_amount": new_loan_amount or 500000,
                "tenure_months": new_tenure_months or 60,
                "emi": 10000,
                "best_rate": 9.5
            },
            "differences": {
                "emi_change": 0,
                "total_cost_change": 0,
                "interest_savings": 0
            }
        }
    
    @staticmethod
    def get_lenders_info() -> Dict[str, Any]:
        """
        Get information about available lenders.
        
        Returns:
            Dictionary with lender information
        """
        lenders_data = _load_lenders_data()
        
        lenders_info = {}
        for lender_id, lender_data in lenders_data.items():
            lenders_info[lender_id] = {
                "name": lender_data.get("name", ""),
                "type": lender_data.get("type", ""),
                "jurisdiction": lender_data.get("jurisdiction", ""),
                "base_rate": lender_data.get("base_rate", ""),
                "min_loan_amount": lender_data.get("min_loan_amount", ""),
                "max_loan_amount": lender_data.get("max_loan_amount", ""),
                "approval_probability": lender_data.get("approval_probability", "")
            }
        
        return {
            "count": len(lenders_info),
            "lenders": lenders_info
        }
    
    @staticmethod
    def check_eligibility_only(
        loan_amount: float,
        tenure_months: int,
        credit_score: int,
        monthly_salary: float,
        age: int = 35,
        existing_obligations: float = 0
    ) -> Dict[str, Any]:
        """
        Quick eligibility check without full comparison.
        
        Args:
            Same as get_loan_comparisons
        
        Returns:
            Dictionary with:
            - overall_eligible: bool
            - eligible_lenders: List of eligible lender IDs
            - failed_checks: Dict of checks that failed
        """
        engine = LoanComparisonEngine()
        
        result = engine.compare_loans(
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            credit_score=credit_score,
            monthly_salary=monthly_salary,
            age=age,
            existing_obligations=existing_obligations
        )
        
        eligible_lenders = [
            offer["lender_id"] for offer in result.get("eligible_offers", [])
        ]
        
        return {
            "overall_eligible": len(eligible_lenders) > 0,
            "eligible_count": len(eligible_lenders),
            "ineligible_count": result.get("ineligible_count", 0),
            "eligible_lenders": eligible_lenders,
            "recommendations": result.get("smart_suggestions", [])
        }


class SessionService:
    """Service for managing user sessions during loan comparison."""
    
    _sessions: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def create_session(
        cls,
        loan_amount: float,
        tenure_months: int,
        credit_score: int,
        monthly_salary: float,
        age: int = 35,
        existing_obligations: float = 0
    ) -> str:
        """
        Create a new session for loan comparison.
        
        Returns:
            Session ID
        """
        import uuid
        from datetime import datetime
        
        session_id = str(uuid.uuid4())
        
        cls._sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "loan_amount": loan_amount,
            "tenure_months": tenure_months,
            "credit_score": credit_score,
            "monthly_salary": monthly_salary,
            "age": age,
            "existing_obligations": existing_obligations,
            "comparison_result": None,
            "selected_lender": None
        }
        
        return session_id
    
    @classmethod
    def get_session(cls, session_id: str) -> Dict[str, Any]:
        """
        Retrieve session data.
        
        Args:
            session_id: Session ID
        
        Returns:
            Session data or None if not found
        """
        return cls._sessions.get(session_id)
    
    @classmethod
    def update_session(cls, session_id: str, **kwargs) -> None:
        """
        Update session data.
        
        Args:
            session_id: Session ID
            **kwargs: Fields to update
        """
        if session_id in cls._sessions:
            cls._sessions[session_id].update(kwargs)
    
    @classmethod
    def close_session(cls, session_id: str) -> None:
        """
        Close and delete a session.
        
        Args:
            session_id: Session ID
        """
        if session_id in cls._sessions:
            del cls._sessions[session_id]
