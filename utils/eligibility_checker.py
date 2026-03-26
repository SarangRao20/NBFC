"""
Eligibility Checker — Validates applicant profile against lender requirements.
"""

from typing import Tuple, List, Dict
from dataclasses import dataclass


@dataclass
class UserProfile:
    """User's financial profile for eligibility checks."""
    credit_score: int
    monthly_salary: float
    age: int
    loan_amount: float
    tenure_months: int
    existing_obligations: float = 0.0  # Monthly EMI of other loans


class EligibilityChecker:
    """Validates applicant eligibility against lender requirements."""
    
    @staticmethod
    def check_credit_score(credit_score: int, min_required: int) -> Tuple[bool, str]:
        """
        Check if credit score meets minimum requirement.
        
        Args:
            credit_score: User's credit score
            min_required: Lender's minimum requirement
        
        Returns:
            (Eligible: bool, Reason: str)
        """
        if credit_score >= min_required:
            return True, f"Credit score {credit_score} >= {min_required} ✓"
        return False, f"Credit score {credit_score} < {min_required} (Required: {min_required})"
    
    @staticmethod
    def check_age(age: int, min_age: int = 21, max_age: int = 60) -> Tuple[bool, str]:
        """
        Check if age is within acceptable range.
        
        Args:
            age: Applicant's age
            min_age: Minimum (default 21)
            max_age: Maximum (default 60)
        
        Returns:
            (Eligible: bool, Reason: str)
        """
        if min_age <= age <= max_age:
            return True, f"Age {age} is within {min_age}-{max_age} ✓"
        return False, f"Age {age} outside acceptable range ({min_age}-{max_age})"
    
    @staticmethod
    def check_income(monthly_salary: float, min_income: float = 15000) -> Tuple[bool, str]:
        """
        Check if monthly income meets minimum.
        
        Args:
            monthly_salary: User's monthly salary
            min_income: Minimum required income
        
        Returns:
            (Eligible: bool, Reason: str)
        """
        if monthly_salary >= min_income:
            return True, f"Income ₹{monthly_salary:,.0f} >= ₹{min_income:,.0f} ✓"
        return False, f"Income ₹{monthly_salary:,.0f} < ₹{min_income:,.0f}"
    
    @staticmethod
    def check_loan_amount(
        loan_amount: float, 
        min_loan: float, 
        max_loan: float
    ) -> Tuple[bool, str]:
        """
        Check if loan amount is within lender's range.
        
        Args:
            loan_amount: Requested loan amount
            min_loan: Lender's minimum
            max_loan: Lender's maximum
        
        Returns:
            (Eligible: bool, Reason: str)
        """
        if min_loan <= loan_amount <= max_loan:
            return True, f"Loan ₹{loan_amount:,.0f} within ₹{min_loan:,.0f}-₹{max_loan:,.0f} ✓"
        
        error_msg = f"Loan ₹{loan_amount:,.0f} outside range"
        if loan_amount < min_loan:
            error_msg += f" (Min: ₹{min_loan:,.0f})"
        else:
            error_msg += f" (Max: ₹{max_loan:,.0f})"
        return False, error_msg
    
    @staticmethod
    def check_tenure(tenure_months: int, valid_tenures: List[int]) -> Tuple[bool, str]:
        """
        Check if tenure is in lender's available options.
        
        Args:
            tenure_months: Requested tenure in months
            valid_tenures: List of valid tenure options
        
        Returns:
            (Eligible: bool, Reason: str)
        """
        if tenure_months in valid_tenures:
            return (
                True, 
                f"Tenure {tenure_months} months available ✓ (Options: {valid_tenures})"
            )
        return (
            False, 
            f"Tenure {tenure_months} not available. Options: {valid_tenures}"
        )
    
    @staticmethod
    def check_foir(
        monthly_emi: float, 
        monthly_salary: float, 
        existing_obligations: float,
        foir_limit: float = 0.50
    ) -> Tuple[bool, str, float]:
        """
        Check Fixed Obligation to Income Ratio (FOIR).
        
        FOIR = (EMI + Existing Obligations) / Monthly Salary
        
        Industry standards:
        - Conservative: FOIR <= 40% (Banks)
        - Moderate: FOIR <= 50% (NBFCs)
        - Aggressive: FOIR <= 55% (Fintech)
        
        Args:
            monthly_emi: Calculated EMI for new loan
            monthly_salary: User's monthly salary
            existing_obligations: Other monthly EMI/debts
            foir_limit: Lender's FOIR limit
        
        Returns:
            (Eligible: bool, Reason: str, Actual_FOIR: float)
        """
        if monthly_salary <= 0:
            return False, "Monthly salary must be > 0", 0.0
        
        total_obligations = monthly_emi + existing_obligations
        foir = total_obligations / monthly_salary
        foir_percentage = foir * 100
        limit_percentage = foir_limit * 100
        
        if foir <= foir_limit:
            return (
                True,
                f"FOIR {foir_percentage:.1f}% <= {limit_percentage:.1f}% ✓ "
                f"(EMI ₹{monthly_emi:,.0f} + Existing ₹{existing_obligations:,.0f} = ₹{total_obligations:,.0f})",
                foir
            )
        
        return (
            False,
            f"FOIR {foir_percentage:.1f}% > {limit_percentage:.1f}% "
            f"(EMI ₹{monthly_emi:,.0f} too high for salary ₹{monthly_salary:,.0f})",
            foir
        )
    
    @staticmethod
    def run_all_checks(
        user_profile: UserProfile,
        lender_offer: Dict
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Run all eligibility checks for a user against a lender.
        
        Args:
            user_profile: User's financial profile
            lender_offer: Lender's requirements from lender_apis
        
        Returns:
            (Overall_Eligible: bool, Passing_Checks: List[str], Failed_Checks: List[str])
        """
        passed = []
        failed = []
        
        # Check 1: Credit Score
        is_pass, msg = EligibilityChecker.check_credit_score(
            user_profile.credit_score,
            lender_offer.get("min_credit_score", 600)
        )
        if is_pass:
            passed.append(msg)
        else:
            failed.append(msg)
        
        # Check 2: Age
        is_pass, msg = EligibilityChecker.check_age(user_profile.age)
        if is_pass:
            passed.append(msg)
        else:
            failed.append(msg)
        
        # Check 3: Income
        is_pass, msg = EligibilityChecker.check_income(user_profile.monthly_salary)
        if is_pass:
            passed.append(msg)
        else:
            failed.append(msg)
        
        # Check 4: Loan Amount
        is_pass, msg = EligibilityChecker.check_loan_amount(
            user_profile.loan_amount,
            lender_offer.get("min_loan_amount", 50000),
            lender_offer.get("max_loan_amount", 5000000)
        )
        if is_pass:
            passed.append(msg)
        else:
            failed.append(msg)
        
        # Check 5: Tenure
        is_pass, msg = EligibilityChecker.check_tenure(
            user_profile.tenure_months,
            lender_offer.get("tenure_options", [12, 24, 36, 48, 60])
        )
        if is_pass:
            passed.append(msg)
        else:
            failed.append(msg)
        
        # Check 6: FOIR (requires EMI calculation)
        # This will be called by comparison engine after EMI is calculated
        
        overall_eligible = len(failed) == 0
        return overall_eligible, passed, failed
    
    @staticmethod
    def get_ineligibility_reasons(
        user_profile: UserProfile,
        lender_offer: Dict
    ) -> List[str]:
        """
        Get list of reasons why user is ineligible.
        
        Returns:
            List of human-readable failure reasons
        """
        _, _, failed = EligibilityChecker.run_all_checks(user_profile, lender_offer)
        return failed
    
    @staticmethod
    def get_suggestions_for_eligibility(
        user_profile: UserProfile,
        failed_checks: List[str]
    ) -> List[str]:
        """
        Provide suggestions to user to become eligible.
        
        Args:
            user_profile: Current user profile
            failed_checks: List of failed checks (reasons)
        
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        
        if any("credit score" in check.lower() for check in failed_checks):
            current = user_profile.credit_score
            needed = 700
            diff = needed - current
            suggestions.append(
                f"🎯 Improve credit score by {diff} points "
                f"(Current: {current}, Target: {needed})\n"
                f"   • Pay bills on time for 3-6 months\n"
                f"   • Reduce existing credit card debt\n"
                f"   • Avoid taking new credit immediately"
            )
        
        if any("age" in check.lower() for check in failed_checks):
            suggestions.append(
                "⚠️ Age requirement not met (Must be 21-60 years)"
            )
        
        if any("income" in check.lower() for check in failed_checks):
            current = user_profile.monthly_salary
            needed = 15000
            diff = needed - current
            suggestions.append(
                f"💼 Increase monthly income by ₹{diff:,.0f} "
                f"(Current: ₹{current:,.0f})"
            )
        
        if any("loan amount" in check.lower() for check in failed_checks):
            suggestions.append(
                f"💰 Reduce requested loan amount or try a different lender\n"
                f"   • Consider a smaller loan (₹{user_profile.loan_amount * 0.75:,.0f})\n"
                f"   • Try NBFC X (allows loans up to ₹30 lakhs)"
            )
        
        if any("FOIR" in check for check in failed_checks):
            suggestions.append(
                f"📊 Reduce monthly EMI by:\n"
                f"   • Extending tenure (5 years → 7 years)\n"
                f"   • Reducing loan amount\n"
                f"   • Paying off existing debts"
            )
        
        return suggestions
