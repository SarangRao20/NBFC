"""
Comparison Agent — LangGraph node for loan comparison in the master workflow.
Fetches, compares, and recommends loans before user selection.
"""

from typing import Dict, Any, Optional
from agents.comparison_engine import LoanComparisonEngine
from agents.master_state import MasterState

# Type alias for convenience
State = MasterState


class ComparisonAgent:
    """
    LangGraph agent node for loan comparison.
    
    Responsibilities:
    1. Extract loan requirements from state
    2. Call comparison engine
    3. Update state with ranked loans
    4. Set flow to wait for user selection
    """
    
    def __init__(self):
        """Initialize comparison agent."""
        self.engine = LoanComparisonEngine()
    
    def extract_requirements(self, state: State) -> Dict[str, Any]:
        """
        Extract loan requirements from state.
        
        Looks for these fields in state (populated by sales agent):
        - loan_amount
        - tenure_months
        - requested_purpose
        - applicant_credit_score
        - applicant_monthly_salary
        - applicant_age
        - existing_monthly_obligations (optional)
        
        Returns:
            Dict with confirmed loan details
        """
        requirements = {
            "loan_amount": state.get("loan_amount"),
            "tenure_months": state.get("tenure_months"),
            "credit_score": state.get("applicant_credit_score", 700),
            "monthly_salary": state.get("applicant_monthly_salary"),
            "age": state.get("applicant_age", 35),
            "existing_obligations": state.get("existing_monthly_obligations", 0),
        }
        
        # Validate all required fields are present
        required = ["loan_amount", "tenure_months", "monthly_salary"]
        missing = [k for k in required if not requirements[k]]
        
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return requirements
    
    def run_comparison(
        self,
        loan_amount: float,
        tenure_months: int,
        credit_score: int,
        monthly_salary: float,
        age: int = 35,
        existing_obligations: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Run the comparison engine.
        
        Args:
            loan_amount: Requested loan amount
            tenure_months: Desired tenure
            credit_score: Applicant's credit score
            monthly_salary: Monthly income
            age: Applicant's age
            existing_obligations: Other monthly EMI
        
        Returns:
            Complete comparison result
        """
        return self.engine.compare_loans(
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            credit_score=credit_score,
            monthly_salary=monthly_salary,
            age=age,
            existing_obligations=existing_obligations,
            auto_weights=True  # Intelligently assign weights
        )
    
    def invoke(self, state: State) -> State:
        """
        Main agent function called by LangGraph.
        
        Flow:
        1. Extract requirements from state
        2. Run comparison engine
        3. Update state with results
        4. Return updated state
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with loan options
        """
        try:
            # Extract requirements
            requirements = self.extract_requirements(state)
            
            print(f"\n[Comparison Agent] Starting loan comparison...")
            print(f"  Loan Amount: ₹{requirements['loan_amount']:,.0f}")
            print(f"  Tenure: {requirements['tenure_months']} months")
            print(f"  Credit Score: {requirements['credit_score']}")
            print(f"  Monthly Salary: ₹{requirements['monthly_salary']:,.0f}")
            
            # Run comparison
            result = self.run_comparison(**requirements)
            
            # Log results
            print(f"\n[Comparison Agent] Results:")
            print(f"  Eligible Offers: {result['eligible_count']}")
            print(f"  Ineligible Offers: {result['ineligible_count']}")
            
            if result["eligible_count"] > 0:
                best = result["best_offer"]
                print(f"  🏆 Best: {best['lender_name']} (Score: {best['composite_score']:.1f})")
                print(f"     EMI: ₹{best['emi']:,.0f} | Rate: {best['interest_rate']}%")
            
            # Update state with results
            state["loan_comparison_result"] = result
            state["loan_options"] = result.get("eligible_offers", [])
            state["best_offer"] = result.get("best_offer")
            state["alternatives"] = result.get("alternatives", [])
            state["comparison_timestamp"] = result.get("comparison_timestamp")
            
            # Set next state based on eligibility
            if result["eligible_count"] > 0:
                state["comparison_status"] = "completed_with_options"
                state["next_step"] = "wait_for_loan_selection"
                print(f"\n[Comparison Agent] Waiting for user to select a loan...")
            else:
                state["comparison_status"] = "no_eligible_options"
                state["next_step"] = "show_suggestions"
                print(f"\n[Comparison Agent] No eligible options. Showing suggestions...")
            
            return state
        
        except ValueError as e:
            print(f"\n[Comparison Agent] Error: {str(e)}")
            state["comparison_status"] = "error"
            state["comparison_error"] = str(e)
            state["next_step"] = "error_handling"
            return state
        except Exception as e:
            print(f"\n[Comparison Agent] Unexpected error: {str(e)}")
            state["comparison_status"] = "error"
            state["comparison_error"] = str(e)
            state["next_step"] = "error_handling"
            return state


class LoanSelectionHandler:
    """
    Handles user selection from comparison results.
    """
    
    @staticmethod
    def process_selection(
        state: State,
        selected_lender_id: str
    ) -> State:
        """
        Process user's loan selection.
        
        Args:
            state: Current state with comparison results
            selected_lender_id: User's selected lender ID
        
        Returns:
            Updated state with selected lender
        """
        # Find selected loan in comparison results
        loan_options = state.get("loan_options", [])
        selected_loan = None
        
        for loan in loan_options:
            if loan.get("lender_id") == selected_lender_id:
                selected_loan = loan
                break
        
        if not selected_loan:
            state["selection_status"] = "error"
            state["selection_error"] = f"Lender {selected_lender_id} not found in options"
            return state
        
        # Update state with selection
        state["selected_lender"] = selected_lender_id
        state["selected_lender_name"] = selected_loan.get("lender_name")
        state["selected_interest_rate"] = selected_loan.get("interest_rate")
        state["selected_emi"] = selected_loan.get("emi")
        state["selected_total_cost"] = selected_loan.get("total_cost")
        state["selected_processing_fee"] = selected_loan.get("processing_fee")
        state["selected_approval_probability"] = selected_loan.get("approval_probability")
        
        state["selection_status"] = "completed"
        state["selection_timestamp"] = __import__("datetime").datetime.now().isoformat()
        
        # Next step is underwriting
        state["next_step"] = "underwriting"
        
        print(f"\n[Selection Handler] User selected: {selected_loan.get('lender_name')}")
        print(f"  EMI: ₹{(selected_loan.get('emi') or 0):,.0f}")
        print(f"  Rate: {selected_loan.get('interest_rate')}%")
        print(f"  Next: Proceeding to underwriting...")
        
        return state


# Global instances for use in LangGraph
comparison_agent = ComparisonAgent()
selection_handler = LoanSelectionHandler()


def run_comparison_agent(state: State) -> State:
    """
    Wrapper function for LangGraph integration.
    Called as a node in the master graph.
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state after comparison
    """
    return comparison_agent.invoke(state)


def run_loan_selection(state: State) -> State:
    """
    Wrapper function for LangGraph integration.
    Called when user selects a loan.
    
    Expects state to contain:
    - selected_lender: The lender ID selected by user (from frontend)
    
    Args:
        state: Current workflow state
    
    Returns:
        Updated state after selection
    """
    selected_lender_id = state.get("selected_lender")
    if not selected_lender_id:
        state["selection_status"] = "error"
        state["selection_error"] = "No lender selected"
        return state
    
    return LoanSelectionHandler.process_selection(state, selected_lender_id)
