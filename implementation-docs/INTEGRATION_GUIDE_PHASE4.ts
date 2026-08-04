/**
 * INTEGRATION GUIDE — How to wire Phase 4 components into your app
 * 
 * Follow these steps to integrate loan comparison UI into your existing React app
 */

// ============================================================================
// STEP 1: Update your AppState type
// ============================================================================
// File: frontend/src/types.ts

import { GetLoansResponse } from './types/comparison';

export interface AppState {
  // ... your existing fields ...
  
  // ADD THESE NEW FIELDS:
  // Loan comparison workflow
  loan_amount?: number;
  tenure_months?: number;
  applicant_credit_score?: number;
  applicant_monthly_salary?: number;
  applicant_age?: number;
  existing_monthly_obligations?: number;
  
  // Comparison results
  loan_comparison_result?: GetLoansResponse;
  selected_lender?: string;
  selected_lender_name?: string;
  selected_interest_rate?: number;
  selected_emi?: number;
  comparison_status?: 'loading' | 'completed' | 'error' | 'idle';
}

// ============================================================================
// STEP 2: Import components in your main App file
// ============================================================================
// File: frontend/src/App.tsx

import LoanComparisonPane from './components/LoanComparisonPane';

// ============================================================================
// STEP 3: Add routing logic in your main render
// ============================================================================
// File: frontend/src/App.tsx (main render function)

function App() {
  // ... your existing code ...
  
  return (
    <div>
      {/* ... your existing components ... */}
      
      {/* ADD THIS SECTION AFTER sales_agent and BEFORE document_agent */}
      {(activeAgent === 'comparison_agent' || nextAgent === 'comparison_agent') && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            💼 Compare Loan Options
          </h2>
          
          <LoanComparisonPane
            {/* Pass the loan parameters from state */}
            loanAmount={state.loan_amount || 0}
            tenureMonths={state.tenure_months || 0}
            creditScore={state.applicant_credit_score || 700}
            monthlySalary={state.applicant_monthly_salary || 0}
            age={state.applicant_age || 35}
            existingObligations={state.existing_monthly_obligations || 0}
            
            {/* Callback when user selects a loan */}
            onLoanSelected={(lenderId, selectedData) => {
              console.log('Loan selected:', lenderId, selectedData);
              
              // UPDATE APP STATE
              setState(prevState => ({
                ...prevState,
                selected_lender: lenderId,
                selected_lender_name: selectedData.lenderName,
                selected_interest_rate: selectedData.interestRate,
                selected_emi: selectedData.emi,
                comparison_status: 'completed',
                
                // Move to next step
                current_phase: 'loan_selection',
                activeAgent: 'loan_selection',
                next_agent: selectedData.nextStep || 'underwriting_agent',
              }));
              
              // Optional: Send update to backend via WebSocket
              if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                  type: 'loan_selected',
                  session_id: state.session_id,
                  selected_lender: lenderId,
                  selected_interest_rate: selectedData.interestRate,
                  selected_emi: selectedData.emi,
                }));
              }
            }}
            
            {/* Optional callback for loading state */}
            onComparingChanged={(isComparing) => {
              console.log('Comparing:', isComparing);
              // Could disable other controls here
            }}
          />
        </div>
      )}
      
      {/* Continue with rest of your agents */}
      {/* document_agent, kyc_agent, etc. */}
    </div>
  );
}

// ============================================================================
// STEP 4: Set up environment variable for API
// ============================================================================
// File: .env.local (for development)

REACT_APP_API_URL=http://localhost:8000

// File: .env.production (for production)

REACT_APP_API_URL=https://your-api-domain.com

// ============================================================================
// STEP 5: Example state initialization
// ============================================================================

const initialState: AppState = {
  // ... existing fields ...
  
  // New fields
  loan_amount: 0,
  tenure_months: 0,
  applicant_credit_score: 700,
  applicant_monthly_salary: 0,
  applicant_age: 35,
  existing_monthly_obligations: 0,
  
  loan_comparison_result: undefined,
  selected_lender: undefined,
  comparison_status: 'idle',
};

// ============================================================================
// STEP 6: Event handler for moving to comparison
// ============================================================================
// File: frontend/src/App.tsx (or wherever you handle agent routing)

function moveToComparison() {
  setState(prevState => ({
    ...prevState,
    activeAgent: 'comparison_agent',
    current_phase: 'comparison',
    
    // Make sure loan details are set (from sales agent)
    loan_amount: prevState.requestedAmount,
    tenure_months: prevState.tenure,
    applicant_credit_score: prevState.creditScore,
    applicant_monthly_salary: prevState.salary,
    applicant_age: 35, // or from user profile
    existing_monthly_obligations: 0, // or from previous data
  }));
}

// ============================================================================
// STEP 7: Example flow diagram
// ============================================================================
/*
 
 sales_agent (user enters: amount, tenure, credit score, salary)
      ↓
 moveToComparison() called
      ↓
 activeAgent = 'comparison_agent'
      ↓
 <LoanComparisonPane /> renders
      ↓
 Fetches loans from API
      ↓
 Displays 5 loan options
      ↓
 User selects loan
      ↓
 onLoanSelected callback fires
      ↓
 setState() updates with selected_lender
      ↓
 next_agent = 'underwriting_agent' OR 'loan_selection'
      ↓
 Router moves to next phase
      ↓
 underwriting_agent continues workflow

*/

// ============================================================================
// STEP 8: Optional - Handle what-if in parent
// ============================================================================
// This is already handled inside LoanComparisonPane, but you can listen:

useEffect(() => {
  if (state.comparison_status === 'completed') {
    console.log('Comparison completed, selected:', state.selected_lender);
    // Trigger any parent-level side effects here
  }
}, [state.comparison_status, state.selected_lender]);

// ============================================================================
// STEP 9: Optional - Styling customization
// ============================================================================
// If you want to customize colors, edit the Tailwind classes in components
// All components use:
//   - bg-blue-600 for primary (change to your brand color)
//   - bg-green-600 for success
//   - bg-red-600 for errors
//   - text-gray-900 for dark text
//
// Find and replace in all components:
// - bg-blue-600 → bg-indigo-600 (if you prefer indigo)
// - text-blue-600 → text-indigo-600
// etc.

// ============================================================================
// STEP 10: Testing checklist
// ============================================================================
/*
 
 ✅ Ensure .env.local has correct API_URL
 ✅ Ensure backend is running (python main.py)
 ✅ Ensure API endpoints are working:
    - POST /api/comparison/get-loans
    - POST /api/comparison/select-loan
    - GET /api/comparison/lenders
 ✅ Check browser console for errors
 ✅ Test on different screen sizes (mobile, tablet, desktop)
 ✅ Test with different credit scores
 ✅ Test what-if simulator
 ✅ Verify WebSocket updates (if applicable)
 ✅ Check network tab for API calls
 
*/

// ============================================================================
// STEP 11: Troubleshooting
// ============================================================================
/*

Issue: "Cannot find module LoanComparisonPane"
Solution: Check that frontend/src/components/LoanComparisonPane.tsx exists

Issue: Component doesn't render
Solution: Check browser console for errors, ensure activeAgent is set correctly

Issue: API calls fail with 404
Solution: 
  1. Check REACT_APP_API_URL in .env.local
  2. Ensure backend server is running
  3. Check backend logs for errors

Issue: Loans don't appear
Solution:
  1. Open Network tab, check API response
  2. Verify response matches GetLoansResponse type
  3. Check console for parse errors

Issue: Selection doesn't trigger callback
Solution:
  1. Verify onLoanSelected prop is passed
  2. Check browser console for errors
  3. Verify lender ID matches loan object

*/
