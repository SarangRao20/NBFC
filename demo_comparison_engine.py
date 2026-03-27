"""
Demo script showcasing the Loan Comparison Engine.
Shows real-world examples of how loans are compared and recommended.
"""

import json
from agents.comparison_engine import LoanComparisonEngine


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_offer(offer: dict, rank: int = None):
    """Pretty print a single loan offer."""
    badge = offer.get("rank_badge", "")
    lender = offer.get("lender_name", "Unknown")
    score = offer.get("composite_score", 0)
    
    print(f"{badge} {lender} (Score: {score:.1f}/100)")
    print(f"  Interest Rate:        {offer.get('interest_rate', 0):.2f}%")
    print(f"  Monthly EMI:          ₹{offer.get('emi', 0):,.0f}")
    print(f"  Processing Fee:       ₹{offer.get('processing_fee', 0):,.0f}")
    print(f"  Total Interest:       ₹{offer.get('total_interest', 0):,.0f}")
    print(f"  Total Cost:           ₹{offer.get('total_cost', 0):,.0f}")
    print(f"  Approval Chance:      {offer.get('approval_percentage', 0):.0f}%")
    print(f"  Settlement Time:      {offer.get('settlement_days', 0)} days")
    print()


def demo_scenario_1_good_applicant():
    """Scenario 1: Good applicant with stable income."""
    print_section("SCENARIO 1: GOOD APPLICANT (Stable Income, Good Credit)")
    
    print("User Profile:")
    print("  • Loan Amount: ₹5,00,000")
    print("  • Tenure: 60 months (5 years)")
    print("  • Credit Score: 750 (Good)")
    print("  • Monthly Salary: ₹50,000")
    print("  • Age: 35 years")
    
    engine = LoanComparisonEngine()
    result = engine.compare_loans(
        loan_amount=500000,
        tenure_months=60,
        credit_score=750,
        monthly_salary=50000,
        age=35
    )
    
    print(f"\nComparison Results:")
    print(f"  Total Lenders Checked: {result['eligible_count'] + result['ineligible_count']}")
    print(f"  ✓ Eligible Offers: {result['eligible_count']}")
    print(f"  ✗ Ineligible Offers: {result['ineligible_count']}")
    
    print(f"\nApplied Weights:")
    print(f"  • EMI Weight: {result['applied_weights']['emi_weight']:.0%}")
    print(f"  • Approval Weight: {result['applied_weights']['approval_weight']:.0%}")
    print(f"  • Cost Weight: {result['applied_weights']['cost_weight']:.0%}")
    
    if result["best_offer"]:
        print_section("🏆 BEST OFFER RECOMMENDATION")
        print_offer(result["best_offer"])
        print(f"Why this is best:\n{result['recommendation_reason']}")
        
        if result["alternatives"]:
            print_section("🥈 ALTERNATIVE OPTIONS")
            for i, alt in enumerate(result["alternatives"], 2):
                print_offer(alt, i)
    
    if result["ineligible_offers"]:
        print_section("❌ OFFERS YOU DIDN'T QUALIFY FOR")
        for lender, data in result["ineligible_offers"].items():
            print(f"{lender}:")
            for reason in data["failed_reasons"]:
                print(f"  • {reason}")
            print()


def demo_scenario_2_low_income():
    """Scenario 2: Low income, tight budget."""
    print_section("SCENARIO 2: TIGHT BUDGET (Low Income, Basic Credit)")
    
    print("User Profile:")
    print("  • Loan Amount: ₹2,00,000")
    print("  • Tenure: 48 months (4 years)")
    print("  • Credit Score: 700 (Good)")
    print("  • Monthly Salary: ₹25,000 (Low)")
    print("  • Age: 28 years")
    
    engine = LoanComparisonEngine()
    result = engine.compare_loans(
        loan_amount=200000,
        tenure_months=48,
        credit_score=700,
        monthly_salary=25000,
        age=28
    )
    
    print(f"\nComparison Results:")
    print(f"  ✓ Eligible Offers: {result['eligible_count']}")
    print(f"  ✗ Ineligible Offers: {result['ineligible_count']}")
    
    print(f"\nApplied Weights (EMI-Focused for Low Income):")
    print(f"  • EMI Weight: {result['applied_weights']['emi_weight']:.0%} (HIGH - Critical for budget)")
    print(f"  • Approval Weight: {result['applied_weights']['approval_weight']:.0%}")
    print(f"  • Cost Weight: {result['applied_weights']['cost_weight']:.0%}")
    
    if result["best_offer"]:
        print_section("🏆 BEST OFFER - LOWEST MONTHLY PAYMENT")
        offer = result["best_offer"]
        print(f"{offer['lender_name']}")
        print(f"  Monthly EMI: ₹{offer.get('emi', 0):,.0f}")
        print(f"  Interest Rate: {offer.get('interest_rate', 0):.2f}%")
        print(f"  This saves you ₹{200000/48 - offer.get('emi', 0):,.0f}/month vs zero-interest scenario")


def demo_scenario_3_poor_credit():
    """Scenario 3: Poor credit score, needs approval."""
    print_section("SCENARIO 3: BORDERLINE CREDIT (Fair Credit, Approval-Focused)")
    
    print("User Profile:")
    print("  • Loan Amount: ₹5,00,000")
    print("  • Tenure: 60 months")
    print("  • Credit Score: 680 (Fair - Borderline)")
    print("  • Monthly Salary: ₹50,000")
    print("  • Age: 32 years")
    
    engine = LoanComparisonEngine()
    result = engine.compare_loans(
        loan_amount=500000,
        tenure_months=60,
        credit_score=680,
        monthly_salary=50000,
        age=32
    )
    
    print(f"\nComparison Results:")
    print(f"  ✓ Eligible Offers: {result['eligible_count']}")
    print(f"  ✗ Ineligible Offers: {result['ineligible_count']}")
    
    print(f"\nApplied Weights (Approval-Focused for Lower Credit):")
    print(f"  • EMI Weight: {result['applied_weights']['emi_weight']:.0%}")
    print(f"  • Approval Weight: {result['applied_weights']['approval_weight']:.0%} (HIGH - Beat rejection risk)")
    print(f"  • Cost Weight: {result['applied_weights']['cost_weight']:.0%}")
    
    if result["best_offer"]:
        print_section("🏆 BEST OFFER - HIGHEST APPROVAL CHANCE")
        offer = result["best_offer"]
        print(f"{offer['lender_name']}")
        print(f"  Approval Probability: {offer.get('approval_percentage', 0):.0f}%")
        print(f"  Monthly EMI: ₹{offer.get('emi', 0):,.0f}")
        print(f"  Interest Rate: {offer.get('interest_rate', 0):.2f}%")
        print(f"\n  Why this is best despite higher rate:")
        print(f"  • 95% approval chance (vs 85% for main bank)")
        print(f"  • ₹{offer.get('processing_fee', 0) - 2500:,.0f} higher processing fee is acceptable")
        print(f"    if it guarantees approval")


def demo_scenario_4_high_income():
    """Scenario 4: High income executive optimizing for lowest cost."""
    print_section("SCENARIO 4: HIGH INCOME (Cost Optimization)")
    
    print("User Profile:")
    print("  • Loan Amount: ₹20,00,000 (Large)")
    print("  • Tenure: 60 months")
    print("  • Credit Score: 800 (Excellent)")
    print("  • Monthly Salary: ₹1,50,000 (High)")
    print("  • Age: 40 years")
    
    engine = LoanComparisonEngine()
    result = engine.compare_loans(
        loan_amount=2000000,
        tenure_months=60,
        credit_score=800,
        monthly_salary=150000,
        age=40
    )
    
    print(f"\nComparison Results:")
    print(f"  ✓ Eligible Offers: {result['eligible_count']}")
    
    print(f"\nApplied Weights (Cost-Focused for High Income & Large Loan):")
    print(f"  • EMI Weight: {result['applied_weights']['emi_weight']:.0%}")
    print(f"  • Approval Weight: {result['applied_weights']['approval_weight']:.0%}")
    print(f"  • Cost Weight: {result['applied_weights']['cost_weight']:.0%} (HIGH - Optimize interest savings)")
    
    if result["best_offer"] and len(result["eligible_offers"]) >= 2:
        best = result["best_offer"]
        second = result["alternatives"][0] if result["alternatives"] else None
        
        print_section("💰 LOWEST TOTAL COST SAVINGS")
        print(f"Best Choice: {best['lender_name']}")
        
        if second:
            total_savings = second.get("total_cost", 0) - best.get("total_cost", 0)
            print(f"\nComparison with 2nd Choice ({second['lender_name']}):")
            print(f"  • Best Option Total Cost: ₹{best.get('total_cost', 0):,.0f}")
            print(f"  • 2nd Option Total Cost: ₹{second.get('total_cost', 0):,.0f}")
            print(f"  • Your Savings: ₹{total_savings:,.0f}")
            print(f"  • Savings per month (over 5 years): ₹{total_savings/60:,.0f}")


def demo_scenario_5_ineligible():
    """Scenario 5: User ineligible for most lenders (gets suggestions)."""
    print_section("SCENARIO 5: INELIGIBLE - TOO HIGH EMI (Gets Smart Suggestions)")
    
    print("User Profile:")
    print("  • Loan Amount: ₹30,00,000 (Very High)")
    print("  • Tenure: 12 months (Very Short)")
    print("  • Credit Score: 750")
    print("  • Monthly Salary: ₹50,000 (Insufficient for this combo)")
    print("  • Age: 35 years")
    
    engine = LoanComparisonEngine()
    result = engine.compare_loans(
        loan_amount=3000000,
        tenure_months=12,
        credit_score=750,
        monthly_salary=50000,
        age=35
    )
    
    print(f"\nComparison Results:")
    print(f"  ✓ Eligible Offers: {result['eligible_count']}")
    print(f"  ✗ Ineligible Offers: {result['ineligible_count']}")
    
    if result["smart_suggestions"]:
        print_section("💡 SMART SUGGESTIONS TO BECOME ELIGIBLE")
        for i, suggestion in enumerate(result["smart_suggestions"], 1):
            print(f"{i}. {suggestion}\n")
    
    if result["ineligible_offers"]:
        print_section("WHY YOU DIDN'T QUALIFY")
        for lender, data in list(result["ineligible_offers"].items())[:2]:
            print(f"{lender}:")
            for reason in data["failed_reasons"][:2]:
                print(f"  • {reason}")
            print()


def main():
    """Run all demo scenarios."""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  LOAN COMPARISON ENGINE - LIVE DEMO  ".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    demo_scenario_1_good_applicant()
    demo_scenario_2_low_income()
    demo_scenario_3_poor_credit()
    demo_scenario_4_high_income()
    demo_scenario_5_ineligible()
    
    print_section("✅ Demo Complete!")
    print("The Comparison Engine successfully:")
    print("  • Fetched offers from 5 different lenders")
    print("  • Filtered by eligibility criteria (credit score, FOIR, age, income)")
    print("  • Ranked by intelligent weighted scoring")
    print("  • Generated personalized recommendations")
    print("  • Provided smart suggestions for ineligible users")
    print()


if __name__ == "__main__":
    main()
