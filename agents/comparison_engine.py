"""
Loan Comparison Engine — Core orchestration for comparing loans across lenders.
Handles EMI calculation, eligibility checking, ranking, and recommendations.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from mock_apis.lender_apis import aggregate_lender_offers
from utils.eligibility_checker import EligibilityChecker, UserProfile
from utils.loan_ranker import LoanRanker, WeightAssigner


class LoanComparisonEngine:
    """
    Orchestrates the complete loan comparison process.
    
    Flow:
    1. Fetch offers from all lenders
    2. Calculate EMI and costs for each offer
    3. Filter by eligibility rules
    4. Rank by weighted scoring
    5. Generate recommendations and explanations
    """
    
    def __init__(self):
        """Initialize comparison engine."""
        self.default_weights = (0.40, 0.35, 0.25)  # EMI, Approval, Cost
    
    # ============================================================================
    # STAGE 1: EMI & COST CALCULATION
    # ============================================================================
    
    @staticmethod
    def calculate_emi(
        principal: float,
        annual_rate: float,
        tenure_months: int
    ) -> float:
        """
        Calculate monthly EMI using standard reducing-balance formula.
        
        Formula: EMI = P × r × (1+r)^n / [(1+r)^n - 1]
        where:
          P = Principal (loan amount)
          r = Monthly interest rate (annual_rate / 12 / 100)
          n = Number of months (tenure_months)
        
        Args:
            principal: Loan amount in INR
            annual_rate: Annual interest rate (%)
            tenure_months: Loan tenure in months
        
        Returns:
            Monthly EMI amount (rounded to 2 decimals)
        
        Example:
            principal=500000, annual_rate=10.5%, tenure_months=60
            → EMI ≈ ₹9,735
        """
        if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
            return 0.0
        
        monthly_rate = annual_rate / (12 * 100)
        
        # Handle zero rate case
        if monthly_rate == 0:
            return round(principal / tenure_months, 2)
        
        numerator = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months)
        denominator = ((1 + monthly_rate) ** tenure_months) - 1
        
        emi = numerator / denominator
        return round(emi, 2)
    
    @staticmethod
    def calculate_loan_metrics(
        loan_amount: float,
        interest_rate: float,
        tenure_months: int,
        processing_fee: float
    ) -> Dict:
        """
        Calculate comprehensive loan metrics.
        
        Args:
            loan_amount: Principal borrowed
            interest_rate: Annual interest rate (%)
            tenure_months: Loan tenure in months
            processing_fee: One-time processing fee in INR
        
        Returns:
            Dict with:
            - emi: Monthly payment
            - total_repayment: emi × tenure_months
            - total_interest: total_repayment - loan_amount
            - total_cost: total_interest + processing_fee
            - effective_rate: Adjusted for fees
        """
        emi = LoanComparisonEngine.calculate_emi(loan_amount, interest_rate, tenure_months)
        
        if emi == 0:
            return {
                "emi": 0,
                "total_repayment": 0,
                "total_interest": 0,
                "total_cost": processing_fee,
                "effective_rate": 0,
            }
        
        total_repayment = emi * tenure_months
        total_interest = total_repayment - loan_amount
        total_cost = total_interest + processing_fee
        
        # Effective rate adjusted for processing fee
        # (Total Cost / Principal) / (Tenure in Years) × 100
        effective_rate = (total_cost / loan_amount) / (tenure_months / 12) * 100
        
        return {
            "emi": emi,
            "total_repayment": round(total_repayment, 2),
            "total_interest": round(total_interest, 2),
            "total_cost": round(total_cost, 2),
            "effective_rate": round(effective_rate, 2),
        }
    
    # ============================================================================
    # STAGE 2: ELIGIBILITY FILTERING
    # ============================================================================
    
    @staticmethod
    def validate_and_enrich_offers(
        raw_offers: List[Dict],
        user_profile: UserProfile
    ) -> Tuple[List[Dict], Dict]:
        """
        Validate each offer against eligibility rules and calculate metrics.
        
        Args:
            raw_offers: Raw offers from lender APIs
            user_profile: User's financial profile
        
        Returns:
            (eligible_offers: List, ineligible_offers_with_reasons: Dict)
        """
        eligible_offers = []
        ineligible_offers = {}
        
        for offer in raw_offers:
            # Calculate EMI first
            metrics = LoanComparisonEngine.calculate_loan_metrics(
                loan_amount=user_profile.loan_amount,
                interest_rate=offer.get("interest_rate", 10.0),
                tenure_months=user_profile.tenure_months,
                processing_fee=offer.get("processing_fee", 0)
            )
            
            # Add metrics to offer
            enriched_offer = {**offer, **metrics}
            
            # Run eligibility checks
            overall_eligible, passed, failed = EligibilityChecker.run_all_checks(
                user_profile, 
                offer
            )
            
            # Check FOIR (requires EMI)
            is_foir_pass, foir_msg, foir_ratio = EligibilityChecker.check_foir(
                monthly_emi=metrics["emi"],
                monthly_salary=user_profile.monthly_salary,
                existing_obligations=user_profile.existing_obligations,
                foir_limit=offer.get("foir_limit", 0.50)
            )
            
            if is_foir_pass:
                passed.append(foir_msg)
            else:
                failed.append(foir_msg)
                overall_eligible = False
            
            # Store results
            if overall_eligible:
                enriched_offer["eligibility_checks"] = {
                    "passed": passed,
                    "failed": failed,
                    "overall": True,
                }
                enriched_offer["foir"] = round(foir_ratio, 4)
                eligible_offers.append(enriched_offer)
            else:
                ineligible_offers[offer["lender_name"]] = {
                    "offer": enriched_offer,
                    "failed_reasons": failed,
                    "passed_checks": passed,
                }
        
        return eligible_offers, ineligible_offers
    
    # ============================================================================
    # STAGE 3: RANKING & SCORING
    # ============================================================================
    
    @staticmethod
    def rank_eligible_offers(
        eligible_offers: List[Dict],
        weights: Optional[Tuple[float, float, float]] = None
    ) -> List[Dict]:
        """
        Rank eligible offers using weighted scoring.
        
        Args:
            eligible_offers: Pre-filtered eligible loan offers
            weights: (emi_weight, approval_weight, cost_weight)
                    If None, uses default balanced weights
        
        Returns:
            Ranked list of offers with scores and recommendations
        """
        if not eligible_offers:
            return []
        
        if weights is None:
            weights = (0.40, 0.35, 0.25)
        
        ranker = LoanRanker(*weights)
        
        # Prepare loans dict for ranker
        loans_to_rank = []
        for offer in eligible_offers:
            loans_to_rank.append({
                "lender_name": offer["lender_name"],
                "lender_id": offer["lender_id"],
                "emi": offer["emi"],
                "total_cost": offer["total_cost"],
                "approval_probability": offer["approval_probability"],
                "approval_percentage": offer["approval_probability"] * 100,
                "interest_rate": offer["interest_rate"],
                "processing_fee": offer["processing_fee"],
                # Include all offer details for output
                **{k: v for k, v in offer.items() 
                   if k not in ["emi", "total_cost", "approval_probability"]}
            })
        
        # Rank offers
        ranked = ranker.rank_offers(loans_to_rank)
        
        return ranked
    
    # ============================================================================
    # STAGE 4: RECOMMENDATION GENERATION
    # ============================================================================
    
    @staticmethod
    def generate_recommendations(
        ranked_offers: List[Dict]
    ) -> Dict:
        """
        Generate smart recommendations from ranked offers.
        
        Args:
            ranked_offers: Ranked and scored offers
        
        Returns:
            Dict with:
            - best_offer: #1 recommendation
            - alternatives: #2 and #3 options
            - recommendation_reasons: Explanations
        """
        if not ranked_offers:
            return {
                "best_offer": None,
                "alternatives": [],
                "recommendation_reasons": "",
            }
        
        best = ranked_offers[0]
        alternatives = ranked_offers[1:3]  # Get top 2 alternatives
        
        # Generate reason for best offer
        reason = LoanRanker.get_recommendation_reason(best, alternatives) if alternatives else f"{best['lender_name']}: Best overall score"
        
        return {
            "best_offer": best,
            "alternatives": alternatives,
            "recommendation_reasons": reason,
            "best_offer_badge": LoanRanker.get_rank_badge(1),
        }
    
    @staticmethod
    def generate_smart_suggestions(
        user_profile: UserProfile,
        ineligible_offers: Dict
    ) -> List[str]:
        """
        Generate smart suggestions for ineligible users.
        
        Args:
            user_profile: User's profile
            ineligible_offers: Dict of failed offers with reasons
        
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        
        if not ineligible_offers:
            return suggestions
        
        # Check if FOIR is a common issue
        foir_failures = [
            name for name, data in ineligible_offers.items()
            if any("FOIR" in reason for reason in data["failed_reasons"])
        ]
        
        if len(foir_failures) >= 2:
            # Most lenders rejected due to FOIR
            new_tenure = user_profile.tenure_months + 12
            new_emi = LoanComparisonEngine.calculate_emi(
                user_profile.loan_amount,
                12.0,  # Average rate
                new_tenure
            )
            current_emi = LoanComparisonEngine.calculate_emi(
                user_profile.loan_amount,
                12.0,
                user_profile.tenure_months
            )
            savings = current_emi - new_emi
            
            suggestions.append(
                f"📊 Extend tenure to {new_tenure} months\n"
                f"   • Save ₹{savings:,.0f}/month in EMI\n"
                f"   • EMI reduces from ₹{current_emi:,.0f} to ₹{new_emi:,.0f}"
            )
            
            new_amount = user_profile.loan_amount * 0.80
            new_emi_low = LoanComparisonEngine.calculate_emi(
                new_amount,
                12.0,
                user_profile.tenure_months
            )
            reduction = current_emi - new_emi_low
            
            suggestions.append(
                f"💰 Reduce loan amount to ₹{new_amount:,.0f}\n"
                f"   • Save ₹{reduction:,.0f}/month in EMI\n"
                f"   • Borrow ₹{user_profile.loan_amount - new_amount:,.0f} less"
            )
        
        # Check if credit score is issue
        credit_failures = [
            name for name, data in ineligible_offers.items()
            if any("credit score" in reason.lower() for reason in data["failed_reasons"])
        ]
        
        if credit_failures:
            suggestions.append(
                f"📈 Improve credit score (Current: {user_profile.credit_score})\n"
                f"   • Pay bills on time for 3-6 months\n"
                f"   • Reduce credit card debt\n"
                f"   • Avoid new credit applications"
            )
        
        return suggestions
    
    # ============================================================================
    # MAIN ORCHESTRATION METHOD
    # ============================================================================
    
    def compare_loans(
        self,
        loan_amount: float,
        tenure_months: int,
        credit_score: int,
        monthly_salary: float,
        age: int = 35,
        existing_obligations: float = 0.0,
        weights: Optional[Tuple[float, float, float]] = None,
        auto_weights: bool = True
    ) -> Dict:
        """
        Complete loan comparison and recommendation.
        
        This is the main entry point that orchestrates the entire flow.
        
        Args:
            loan_amount: Requested loan in INR
            tenure_months: Desired tenure in months
            credit_score: Applicant's CIBIL score
            monthly_salary: Monthly salary in INR
            age: Applicant's age (default 35)
            existing_obligations: Monthly EMI of other loans (default 0)
            weights: Optional tuple (emi_w, approval_w, cost_w)
            auto_weights: If True, auto-assign weights based on profile
        
        Returns:
            Comprehensive comparison result with:
            - eligible_offers: List of ranked loan options
            - best_offer: Top recommendation
            - alternatives: 2nd and 3rd choices
            - recommendations: Explanation of best choice
            - smart_suggestions: Tips for ineligible users
            - ineligible_offers: Offers user didn't qualify for
            - timestamp: When comparison was done
        """
        # Create user profile
        user_profile = UserProfile(
            credit_score=credit_score,
            monthly_salary=monthly_salary,
            age=age,
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            existing_obligations=existing_obligations,
        )
        
        # STEP 1: Fetch offers from all lenders
        raw_lender_data = aggregate_lender_offers(
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            credit_score=credit_score,
            monthly_salary=monthly_salary,
        )
        
        # STEP 2: Validate and enrich offers
        eligible_offers, ineligible_offers = self.validate_and_enrich_offers(
            raw_offers=raw_lender_data["offers"],
            user_profile=user_profile
        )
        
        # STEP 3: Auto-assign weights if requested
        if auto_weights and weights is None:
            emi_w, app_w, cost_w = WeightAssigner.select_optimal_weights({
                "credit_score": credit_score,
                "monthly_salary": monthly_salary,
                "loan_amount": loan_amount,
            })
            weights = (emi_w, app_w, cost_w)
        elif weights is None:
            weights = self.default_weights
        
        # STEP 4: Rank eligible offers
        ranked_offers = self.rank_eligible_offers(eligible_offers, weights)
        
        # STEP 5: Generate recommendations
        recommendations = self.generate_recommendations(ranked_offers)
        
        # STEP 6: Generate smart suggestions for ineligible
        smart_suggestions = self.generate_smart_suggestions(
            user_profile,
            ineligible_offers
        )
        
        # STEP 7: Build final response
        return {
            "status": "success" if eligible_offers else "no_eligible_offers",
            "eligible_count": len(eligible_offers),
            "ineligible_count": len(ineligible_offers),
            "eligible_offers": ranked_offers,
            "best_offer": recommendations["best_offer"],
            "alternatives": recommendations["alternatives"],
            "recommendation_reason": recommendations["recommendation_reasons"],
            "best_offer_badge": recommendations.get("best_offer_badge"),
            "smart_suggestions": smart_suggestions,
            "ineligible_offers": ineligible_offers,
            "applied_weights": {
                "emi_weight": weights[0],
                "approval_weight": weights[1],
                "cost_weight": weights[2],
            },
            "user_profile": {
                "loan_amount": loan_amount,
                "tenure_months": tenure_months,
                "credit_score": credit_score,
                "monthly_salary": monthly_salary,
                "age": age,
            },
            "comparison_timestamp": datetime.now().isoformat(),
        }
