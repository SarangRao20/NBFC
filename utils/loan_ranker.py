"""
Loan Ranker — Scores and ranks loan offers based on weighted criteria.
"""

from typing import List, Dict, Tuple, Optional
import math


class LoanRanker:
    """Ranks loan offers using weighted scoring algorithm."""
    
    def __init__(self, 
                 emi_weight: float = 0.40,
                 approval_weight: float = 0.35,
                 cost_weight: float = 0.25):
        """
        Initialize ranker with weight distribution.
        
        Args:
            emi_weight: Weight for EMI factor (0-1)
            approval_weight: Weight for approval probability (0-1)
            cost_weight: Weight for total cost (0-1)
        
        Note: Weights should sum to 1.0
        """
        total = emi_weight + approval_weight + cost_weight
        
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        self.emi_weight = emi_weight
        self.approval_weight = approval_weight
        self.cost_weight = cost_weight
    
    @staticmethod
    def normalize_score(
        value: float,
        min_val: float,
        max_val: float,
        invert: bool = False
    ) -> float:
        """
        Normalize a value to 0-100 scale.
        
        Args:
            value: Value to normalize
            min_val: Minimum value in dataset
            max_val: Maximum value in dataset
            invert: If True, lower values get higher scores (for EMI, cost)
        
        Returns:
            Normalized score (0-100)
        
        Example:
            EMI: ₹5,000 (best) → 100, ₹8,000 (worst) → 62.5
            Approval: 85% → 85, 95% → 95
        """
        if min_val == max_val:
            return 100.0
        
        if invert:
            # For metrics where lower is better (EMI, cost)
            # Best (lowest) gets 100, worst (highest) gets lower score
            return ((max_val - value) / (max_val - min_val)) * 100
        else:
            # For metrics where higher is better (approval probability)
            return ((value - min_val) / (max_val - min_val)) * 100
    
    def calculate_emi_score(self, loan_emi: float, min_emi: float, max_emi: float) -> float:
        """
        Calculate score for EMI (lower is better).
        
        Args:
            loan_emi: This loan's EMI
            min_emi: Lowest EMI among all offers
            max_emi: Highest EMI among all offers
        
        Returns:
            EMI score (0-100), where lower EMI = higher score
        """
        return self.normalize_score(loan_emi, min_emi, max_emi, invert=True)
    
    def calculate_approval_score(self, approval_probability: float) -> float:
        """
        Calculate score for approval probability (higher is better).
        
        Note: Approval probability is already 0-100, just use directly
        
        Args:
            approval_probability: Probability as decimal (0.85 = 85%)
        
        Returns:
            Approval score (0-100)
        """
        return approval_probability * 100
    
    def calculate_cost_score(self, total_cost: float, min_cost: float, max_cost: float) -> float:
        """
        Calculate score for total cost (lower is better).
        
        Total Cost = Total Interest + Processing Fee
        
        Args:
            total_cost: This loan's total cost
            min_cost: Lowest cost among all offers
            max_cost: Highest cost among all offers
        
        Returns:
            Cost score (0-100), where lower cost = higher score
        """
        return self.normalize_score(total_cost, min_cost, max_cost, invert=True)
    
    def calculate_composite_score(
        self,
        emi_score: float,
        approval_score: float,
        cost_score: float
    ) -> float:
        """
        Calculate final composite score using weighted formula.
        
        Formula:
            Final Score = (EMI_Score × w1) + (Approval_Score × w2) + (Cost_Score × w3)
        
        Where: w1 + w2 + w3 = 1.0
        
        Args:
            emi_score: Score for EMI (0-100)
            approval_score: Score for approval (0-100)
            cost_score: Score for total cost (0-100)
        
        Returns:
            Final composite score (0-100)
        """
        composite = (
            (emi_score * self.emi_weight) +
            (approval_score * self.approval_weight) +
            (cost_score * self.cost_weight)
        )
        return round(composite, 2)
    
    def rank_offers(self, loans: List[Dict]) -> List[Dict]:
        """
        Rank and score all loan offers.
        
        Args:
            loans: List of loan dictionaries with keys:
                - emi: Monthly EMI
                - total_cost: Total interest + fees
                - approval_probability: Probability (0-1)
                - lender_name: Lender name for display
                - (other offer details)
        
        Returns:
            List of loans with added:
            - emi_score: Score for EMI (0-100)
            - approval_score: Score for approval (0-100)
            - cost_score: Score for total cost (0-100)
            - composite_score: Final ranking score (0-100)
            - recommendation_rank: 1st, 2nd, 3rd, etc.
        
        Raises:
            ValueError: If loans list is empty or missing required keys
        """
        if not loans:
            raise ValueError("loans list cannot be empty")
        
        required_keys = {"emi", "total_cost", "approval_probability", "lender_name"}
        for loan in loans:
            if not required_keys.issubset(loan.keys()):
                raise ValueError(f"Each loan must have keys: {required_keys}")
        
        # Extract min/max values for normalization
        emis = [loan["emi"] for loan in loans]
        costs = [loan["total_cost"] for loan in loans]
        
        min_emi = min(emis)
        max_emi = max(emis)
        min_cost = min(costs)
        max_cost = max(costs)
        
        # Calculate scores for each loan
        scored_loans = []
        for loan in loans:
            emi_score = self.calculate_emi_score(loan["emi"], min_emi, max_emi)
            approval_score = self.calculate_approval_score(loan["approval_probability"])
            cost_score = self.calculate_cost_score(loan["total_cost"], min_cost, max_cost)
            composite_score = self.calculate_composite_score(emi_score, approval_score, cost_score)
            
            scored_loans.append({
                **loan,
                "emi_score": emi_score,
                "approval_score": approval_score,
                "cost_score": cost_score,
                "composite_score": composite_score,
            })
        
        # Sort by composite score (descending)
        ranked_loans = sorted(scored_loans, key=lambda x: x["composite_score"], reverse=True)
        
        # Add rank and recommendation badge
        badges = {0: "🥇 BEST", 1: "🥈 GOOD", 2: "🥉 SOLID"}
        for idx, loan in enumerate(ranked_loans):
            loan["recommendation_rank"] = idx + 1
            loan["rank_badge"] = badges.get(idx, "")
        
        return ranked_loans
    
    @staticmethod
    def get_recommendation_reason(ranked_loan: Dict, alternatives: List[Dict] = None) -> str:
        """
        Generate human-readable explanation for recommendation.
        
        Args:
            ranked_loan: The recommended loan (from ranked list)
            alternatives: Other ranked loans for comparison
        
        Returns:
            Explanation string with key reasons
        """
        lender = ranked_loan.get("lender_name", "Unknown")
        emi = ranked_loan.get("emi", 0)
        rate = ranked_loan.get("interest_rate", 0)
        cost = ranked_loan.get("total_cost", 0)
        approval = ranked_loan.get("approval_percentage", 0)
        
        reasons = []
        
        # Determine why this loan is best
        if ranked_loan.get("emi_score", 0) >= 90:
            reasons.append("Lowest monthly payment")
        
        if ranked_loan.get("approval_score", 0) >= 90:
            reasons.append("Highest approval probability")
        
        if ranked_loan.get("cost_score", 0) >= 85:
            reasons.append("Lowest total cost")
        
        if ranked_loan.get("approval_score", 0) >= 85 and ranked_loan.get("emi_score", 0) >= 80:
            reasons.append("Balanced for approval and affordability")
        
        # Compare with second choice if available
        if alternatives and len(alternatives) > 0:
            second = alternatives[0]
            emi_diff = second.get("emi", 0) - emi
            cost_diff = second.get("total_cost", 0) - cost
            
            if emi_diff > 0:
                reasons.append(f"Save ₹{emi_diff:,.0f}/month vs 2nd choice")
            if cost_diff > 0:
                reasons.append(f"Save ₹{cost_diff:,.0f} total vs 2nd choice")
        
        # Create final recommendation text
        if not reasons:
            reasons = ["Best overall score among eligible options"]
        
        return f"{lender}: " + " • ".join(reasons)
    
    @staticmethod
    def get_rank_badge(rank: int) -> str:
        """Get visual badge for ranking position."""
        badges = {
            1: "🥇 BEST CHOICE",
            2: "🥈 GOOD OPTION",
            3: "🥉 SOLID BACKUP",
        }
        return badges.get(rank, f"#{rank} Option")


class WeightAssigner:
    """Intelligently assigns weights based on user profile."""
    
    @staticmethod
    def assign_by_credit_score(credit_score: int) -> Tuple[float, float, float]:
        """
        Assign weights based on credit score.
        
        Lower credit scores → Higher approval weight
        Higher credit scores → Higher cost weight
        """
        if credit_score >= 800:
            # Excellent: Can negotiate, focus on cost
            return 0.25, 0.15, 0.60
        elif credit_score >= 750:
            # Very Good: Cost-conscious with approval backup
            return 0.35, 0.25, 0.40
        elif credit_score >= 700:
            # Good: Balanced (DEFAULT)
            return 0.40, 0.35, 0.25
        elif credit_score >= 650:
            # Fair: Need approval help
            return 0.25, 0.55, 0.20
        else:
            # Poor: Approval is paramount
            return 0.15, 0.70, 0.15
    
    @staticmethod
    def assign_by_income(monthly_salary: float) -> Tuple[float, float, float]:
        """Assign weights based on income level."""
        if monthly_salary < 25000:
            # Very low: EMI critical
            return 0.65, 0.25, 0.10
        elif monthly_salary < 50000:
            # Low-Mid: Balance EMI and cost
            return 0.50, 0.30, 0.20
        elif monthly_salary < 100000:
            # Mid: Default balanced
            return 0.40, 0.35, 0.25
        else:
            # High: Optimize for cost
            return 0.30, 0.20, 0.50
    
    @staticmethod
    def assign_by_loan_amount(loan_amount: float) -> Tuple[float, float, float]:
        """Assign weights based on loan size."""
        if loan_amount < 300000:
            # Small: Quick approval important
            return 0.35, 0.45, 0.20
        elif loan_amount < 1000000:
            # Medium: Balanced (DEFAULT)
            return 0.40, 0.35, 0.25
        else:
            # Large: Focus on interest savings
            return 0.30, 0.25, 0.45
    
    @staticmethod
    def select_optimal_weights(user_profile: Dict) -> Tuple[float, float, float]:
        """
        Intelligently select weights based on user profile.
        
        Priority: Credit Score > Income > Loan Amount
        
        Args:
            user_profile: Dict with keys:
                - credit_score: int
                - monthly_salary: float
                - loan_amount: float
                - priority: str (optional, overrides auto-selection)
        
        Returns:
            (emi_weight, approval_weight, cost_weight)
        """
        credit_score = user_profile.get("credit_score", 700)
        monthly_salary = user_profile.get("monthly_salary", 50000)
        loan_amount = user_profile.get("loan_amount", 500000)
        
        # RULE 1: Credit score is primary factor (highest impact)
        if credit_score < 650:
            emi_w, app_w, cost_w = 0.15, 0.70, 0.15
        elif credit_score < 700:
            emi_w, app_w, cost_w = 0.25, 0.55, 0.20
        else:
            # Use default balanced for good credit
            emi_w, app_w, cost_w = 0.40, 0.35, 0.25
        
        # RULE 2: Loan amount fine-tunes if very large
        if loan_amount > 2000000:
            # Large loans: Boost cost weight, reduce approval
            emi_w -= 0.05
            cost_w += 0.10
            app_w -= 0.05
        
        # RULE 3: Income affects EMI weight
        if monthly_salary < 35000:
            # Very low: EMI is critical for survival
            emi_w += 0.10
            app_w -= 0.05
            cost_w -= 0.05
        
        # Normalize to ensure sum = 1.0
        total = emi_w + app_w + cost_w
        emi_w = emi_w / total
        app_w = app_w / total
        cost_w = cost_w / total
        
        return round(emi_w, 2), round(app_w, 2), round(cost_w, 2)
