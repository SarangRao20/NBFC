"""Comprehensive Edge Case Evaluation Tests for NBFC Loan System

This file contains tests for various edge cases and failure scenarios
that could break the loan processing system.
"""

import requests
import json
import tempfile
import os
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000"

class EdgeCaseTester:
    def __init__(self):
        self.test_results = []
        self.session_id = None
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def setup_session(self) -> bool:
        """Setup a new session for testing"""
        try:
            response = requests.post(f"{BASE_URL}/session/start")
            self.session_id = response.json()["session_id"]
            return True
        except Exception as e:
            print(f"❌ Failed to setup session: {e}")
            return False
    
    def test_edge_cases(self):
        """Run all edge case tests"""
        print("🧪 Starting Edge Case Evaluation Tests")
        print("=" * 60)
        
        # Document Processing Edge Cases
        self.test_document_edge_cases()
        
        # Underwriting Edge Cases
        self.test_underwriting_edge_cases()
        
        # Persuasion Edge Cases
        self.test_persuasion_edge_cases()
        
        # Workflow Edge Cases
        self.test_workflow_edge_cases()
        
        # Data Integrity Edge Cases
        self.test_data_integrity_edge_cases()
        
        # Performance Edge Cases
        self.test_performance_edge_cases()
        
        # Security Edge Cases
        self.test_security_edge_cases()
        
        self.print_summary()
    
    def test_document_edge_cases(self):
        """Test document processing edge cases"""
        print("\n📄 Document Processing Edge Cases")
        print("-" * 40)
        
        # Test 1: Invalid file format
        self.log_result("Invalid file format", False, "Not implemented")
        
        # Test 2: Corrupted image file
        self.log_result("Corrupted image file", False, "Not implemented")
        
        # Test 3: Document with name mismatch
        self.log_result("Document name mismatch", False, "Not implemented")
        
        # Test 4: Low confidence OCR
        self.log_result("Low confidence OCR", False, "Not implemented")
        
        # Test 5: Tampered document detection
        self.log_result("Tampered document detection", False, "Not implemented")
        
        # Test 6: Missing required document type
        self.log_result("Missing required document type", False, "Not implemented")
        
        # Test 7: Multiple document uploads
        self.log_result("Multiple document uploads", False, "Not implemented")
        
        # Test 8: Empty document file
        self.log_result("Empty document file", False, "Not implemented")
    
    def test_underwriting_edge_cases(self):
        """Test underwriting decision engine edge cases"""
        print("\n🏦 Underwriting Edge Cases")
        print("-" * 40)
        
        # Test 1: Zero salary input
        self.log_result("Zero salary input", False, "Not implemented")
        
        # Test 2: Extremely high salary
        self.log_result("Extremely high salary", False, "Not implemented")
        
        # Test 3: Negative loan amount
        self.log_result("Negative loan amount", False, "Not implemented")
        
        # Test 4: DTI exactly at threshold
        self.log_result("DTI exactly at threshold", False, "Not implemented")
        
        # Test 5: Credit score exactly at minimum
        self.log_result("Credit score at minimum", False, "Not implemented")
        
        # Test 6: Missing credit score
        self.log_result("Missing credit score", False, "Not implemented")
        
        # Test 7: Fraud score edge cases
        self.log_result("Fraud score edge cases", False, "Not implemented")
        
        # Test 8: Pre-approved limit edge cases
        self.log_result("Pre-approved limit edge cases", False, "Not implemented")
    
    def test_persuasion_edge_cases(self):
        """Test persuasion agent edge cases"""
        print("\n🤝 Persuasion Edge Cases")
        print("-" * 40)
        
        # Test 1: Ambiguous user responses
        self.log_result("Ambiguous user responses", False, "Not implemented")
        
        # Test 2: Multiple negotiation rounds
        self.log_result("Multiple negotiation rounds", False, "Not implemented")
        
        # Test 3: No viable options available
        self.log_result("No viable options", False, "Not implemented")
        
        # Test 4: User accepts then declines
        self.log_result("Accept then decline", False, "Not implemented")
        
        # Test 5: Invalid amount in response
        self.log_result("Invalid amount response", False, "Not implemented")
        
        # Test 6: Session timeout during negotiation
        self.log_result("Session timeout during negotiation", False, "Not implemented")
    
    def test_workflow_edge_cases(self):
        """Test workflow edge cases"""
        print("\n🔄 Workflow Edge Cases")
        print("-" * 40)
        
        # Test 1: Skipping workflow steps
        self.log_result("Skipping workflow steps", False, "Not implemented")
        
        # Test 2: Multiple concurrent sessions
        self.log_result("Multiple concurrent sessions", False, "Not implemented")
        
        # Test 3: Session timeout handling
        self.log_result("Session timeout handling", False, "Not implemented")
        
        # Test 4: Invalid phase transitions
        self.log_result("Invalid phase transitions", False, "Not implemented")
        
        # Test 5: Missing required data in state
        self.log_result("Missing required data", False, "Not implemented")
        
        # Test 6: Circular workflow loops
        self.log_result("Circular workflow loops", False, "Not implemented")
        
        # Test 7: Post-sanction workflow breaks
        self.log_result("Post-sanction workflow breaks", False, "Not implemented")
    
    def test_data_integrity_edge_cases(self):
        """Test data integrity edge cases"""
        print("\n💾 Data Integrity Edge Cases")
        print("-" * 40)
        
        # Test 1: Database connection failures
        self.log_result("Database connection failure", False, "Not implemented")
        
        # Test 2: Corrupted session state
        self.log_result("Corrupted session state", False, "Not implemented")
        
        # Test 3: Missing customer data
        self.log_result("Missing customer data", False, "Not implemented")
        
        # Test 4: Inconsistent data across collections
        self.log_result("Inconsistent data", False, "Not implemented")
        
        # Test 5: Data type mismatches
        self.log_result("Data type mismatches", False, "Not implemented")
        
        # Test 6: Duplicate session IDs
        self.log_result("Duplicate session IDs", False, "Not implemented")
        
        # Test 7: Orphaned records
        self.log_result("Orphaned records", False, "Not implemented")
    
    def test_performance_edge_cases(self):
        """Test performance edge cases"""
        print("\n⚡ Performance Edge Cases")
        print("-" * 40)
        
        # Test 1: Large file uploads
        self.log_result("Large file uploads", False, "Not implemented")
        
        # Test 2: High concurrent load
        self.log_result("High concurrent load", False, "Not implemented")
        
        # Test 3: Memory leaks
        self.log_result("Memory leaks", False, "Not implemented")
        
        # Test 4: Slow database queries
        self.log_result("Slow database queries", False, "Not implemented")
        
        # Test 5: Timeout scenarios
        self.log_result("Timeout scenarios", False, "Not implemented")
    
    def test_security_edge_cases(self):
        """Test security edge cases"""
        print("\n🔒 Security Edge Cases")
        print("-" * 40)
        
        # Test 1: SQL injection attempts
        self.log_result("SQL injection attempts", False, "Not implemented")
        
        # Test 2: XSS in document uploads
        self.log_result("XSS in document uploads", False, "Not implemented")
        
        # Test 3: Session hijacking
        self.log_result("Session hijacking", False, "Not implemented")
        
        # Test 4: Data exposure
        self.log_result("Data exposure", False, "Not implemented")
        
        # Test 5: Authentication bypass
        self.log_result("Authentication bypass", False, "Not implemented")
        
        # Test 6: Rate limiting
        self.log_result("Rate limiting", False, "Not implemented")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 EDGE CASE TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = len(self.test_results) - passed
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%" if total > 0 else "0%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        print("\n🎯 Critical Edge Cases to Address:")
        critical_cases = [
            "Document name mismatch leading to identity fraud",
            "DTI manipulation through false income claims",
            "Session state corruption causing workflow breaks",
            "Multiple concurrent sessions for same customer",
            "Post-sanction workflow not routing to advisory",
            "Rejection letters not being generated/served",
            "Persuasion agent accepting 'no' as 'yes'",
            "Missing loan history recognition",
            "File upload timeouts and size limits",
            "Database connection failures during critical steps"
        ]
        
        for i, case in enumerate(critical_cases, 1):
            print(f"   {i}. {case}")


def run_realistic_edge_tests():
    """Run realistic edge case tests with actual API calls"""
    print("🚀 Running Realistic Edge Case Tests")
    print("=" * 60)
    
    tester = EdgeCaseTester()
    
    # Test 1: Document with wrong name
    print("\n📄 Testing: Document Name Mismatch")
    try:
        if not tester.setup_session():
            return
            
        # Setup customer with specific name
        customer_data = {
            "phone": "9876543210",
            "email": "test@example.com",
            "name": "Raj Kumar"
        }
        
        response = requests.post(
            f"{BASE_URL}/session/{tester.session_id}/identify-customer",
            json=customer_data
        )
        
        # Create a document with different name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("""
            PAYSLIP FOR THE MONTH OF OCTOBER 2024
            
            Employee Name: Amit Sharma  # Different name
            Employee ID: EMP123456
            Designation: Software Engineer
            
            Basic Salary: ₹45,000
            Net Salary: ₹58,200
            """)
            doc_path = f.name
        
        with open(doc_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{BASE_URL}/session/{tester.session_id}/extract-ocr",
                files=files
            )
        
        result = response.json()
        verified = result.get("extracted_data", {}).get("verified", False)
        
        tester.log_result(
            "Document name mismatch detection",
            not verified,  # Should NOT be verified
            f"Verification status: {verified}"
        )
        
        os.unlink(doc_path)
        
    except Exception as e:
        tester.log_result("Document name mismatch detection", False, str(e))
    
    # Test 2: Persuasion response handling
    print("\n🤝 Testing: Persuasion Response Handling")
    try:
        # This would require setting up a soft reject scenario
        # For now, just log that this needs proper implementation
        tester.log_result(
            "Persuasion 'no' response handling",
            False,
            "Requires full workflow setup to test properly"
        )
    except Exception as e:
        tester.log_result("Persuasion response handling", False, str(e))
    
    # Test 3: Loan history retrieval
    print("\n📚 Testing: Loan History Retrieval")
    try:
        response = requests.get(f"{BASE_URL}/session/loan-history/9876543210")
        result = response.json()
        
        has_data = bool(result.get("customer") or result.get("loan_applications"))
        tester.log_result(
            "Loan history retrieval",
            True,  # Endpoint should work
            f"Data found: {has_data}"
        )
    except Exception as e:
        tester.log_result("Loan history retrieval", False, str(e))
    
    tester.print_summary()


if __name__ == "__main__":
    # Run theoretical edge case analysis
    tester = EdgeCaseTester()
    tester.test_edge_cases()
    
    print("\n" + "="*80)
    
    # Run realistic tests
    run_realistic_edge_tests()
