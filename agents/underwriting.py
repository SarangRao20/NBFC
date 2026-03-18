import os
import random
from typing import TypedDict, Dict, Any, Tuple
from fpdf import FPDF

class UnderwritingState(TypedDict):
    """LangGraph State for Underwriting Agent"""
    user_name: str
    user_phone: str
    verified_salary: float
    requested_loan_amount: float
    requested_tenure_months: int
    
    # Outcomes
    credit_score: int
    decision: str
    rejection_reasons: list[str]
    emi: float
    sanction_pdf_path: str

def mock_credit_api(phone: str) -> int:
    """Mock Credit Bureau API. Deterministic based on phone number for testing."""
    # To test reject criteria (Score < 700), end phone number in '1' (e.g., 9876543211)
    if phone.endswith('1'):
        return random.randint(500, 680)
    # Excellent score
    return random.randint(750, 850)

def calculate_emi(principal: float, rate_annual: float, months: int) -> float:
    """Standard EMI formula: P x R x (1+R)^N / [(1+R)^N-1]"""
    if months <= 0: return 0.0
    rate_monthly = rate_annual / 12 / 100
    emi = principal * rate_monthly * ((1 + rate_monthly) ** months) / (((1 + rate_monthly) ** months) - 1)
    return round(emi, 2)

def generate_sanction_letter(name: str, amount: float, emi: float, tenure: int) -> str:
    """Generates an automated PDF Sanction Letter using FPDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Header
    pdf.cell(200, 10, txt="NBFC-INC SANCTION LETTER", ln=True, align='C')
    pdf.cell(200, 10, txt="="*40, ln=True, align='C')
    
    # Body
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Date: 15-November-2024", ln=True, align='L')
    pdf.cell(200, 10, txt=f"Applicant Name: {name}", ln=True, align='L')
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=f"Dear {name},\nWe are pleased to inform you that your personal loan application has been carefully reviewed and APPROVED fully unconditionally based on your verified credit profile.")
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="LOAN TERMS:", ln=True, align='L')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Approved Principal Amount: INR {amount:,.2f}", ln=True, align='L')
    pdf.cell(200, 10, txt=f"- Approved Interest Rate: 12.5% p.a.", ln=True, align='L')
    pdf.cell(200, 10, txt=f"- Tenure: {tenure} Months", ln=True, align='L')
    pdf.cell(200, 10, txt=f"- EMI (calculated): INR {emi:,.2f} per month", ln=True, align='L')
    
    pdf.ln(20)
    pdf.cell(200, 10, txt="Best Regards,", ln=True, align='L')
    pdf.cell(200, 10, txt="Automated Underwriting Division, NBFC-INC.", ln=True, align='L')
    
    # Save the PDF to a safe temporary location
    output_path = f"Sanction_Letter_{name.replace(' ', '_')}.pdf"
    pdf.output(output_path)
    return output_path

def run_underwriting(state: UnderwritingState) -> UnderwritingState:
    """Core node representing the 'Master Agent' triggering Underwriting Rules."""
    print("--- UNDERWRITING AGENT: DECISION ENGINE LOOP ---")
    score = mock_credit_api(state["user_phone"])
    state["credit_score"] = score
    state["rejection_reasons"] = []
    
    # 1. Hard Rule: Credit Score Cut-off
    if score < 700:
        state["rejection_reasons"].append(f"Credit Score ({score}) is below the minimum threshold (700) from the Mock Credit Bureau.")
        
    # 2. Hard Rule: DTI (Debt-to-Income / EMI vs Salary limits)
    emi = calculate_emi(state["requested_loan_amount"], 12.5, state["requested_tenure_months"])
    state["emi"] = emi
    
    max_affordable_emi = state["verified_salary"] * 0.50 # Assuming 50% max EMI threshold
    
    if emi > max_affordable_emi:
         state["rejection_reasons"].append(f"Expected EMI (INR {emi:,.2f}) critically exceeds 50% of your verified monthly salary (INR {state['verified_salary']:,.2f}).")
         
    # Final Decision
    if len(state["rejection_reasons"]) > 0:
        state["decision"] = "REJECTED"
        state["sanction_pdf_path"] = ""
    else:
        state["decision"] = "APPROVED"
        # Only Trigger Sanction Agent implicitly if Approved
        state["sanction_pdf_path"] = generate_sanction_letter(
            name=state["user_name"],
            amount=state["requested_loan_amount"],
            emi=state["emi"],
            tenure=state["requested_tenure_months"]
        )
        
    return state
