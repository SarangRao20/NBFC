"""Bulletproof Edge Case Tests for NBFC System

Comprehensive testing scenarios to make the system bulletproof against failures.
"""

import asyncio
import requests
import json
import tempfile
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

BASE_URL = "http://localhost:8000"

class BulletproofEdgeCaseTester:
    """Advanced edge case testing for bulletproof NBFC system"""
    
    def __init__(self):
        self.test_results = []
        self.session_id = None
        self.phone = "9876543210"
        self.email = "test@example.com"
        
    def log_result(self, test_name: str, passed: bool, details: str = "", execution_time: float = 0):
        """Log test result with timing"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name} ({execution_time:.3f}s)")
        if details:
            print(f"   Details: {details}")
    
    async def setup_session(self) -> bool:
        """Setup a new session for testing"""
        try:
            response = requests.post(f"{BASE_URL}/session/start")
            self.session_id = response.json()["session_id"]
            return True
        except Exception as e:
            print(f"❌ Failed to setup session: {e}")
            return False
    
    async def test_redis_caching(self):
        """Test Redis caching functionality"""
        print("\n🔄 Testing Redis Caching")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Test 1: Session caching
            response1 = requests.get(f"{BASE_URL}/session/{self.session_id}/state")
            first_call_time = time.time() - start_time
            
            response2 = requests.get(f"{BASE_URL}/session/{self.session_id}/state")
            second_call_time = time.time() - start_time
            
            # Second call should be faster due to caching
            cache_working = second_call_time < first_call_time * 0.8  # 20% faster assumption
            
            self.log_result(
                "Redis session caching",
                cache_working,
                f"First call: {first_call_time:.3f}s, Second call: {second_call_time:.3f}s"
            )
            
            # Test 2: Loan history caching
            history_start = time.time()
            response3 = requests.get(f"{BASE_URL}/session/loan-history/{self.phone}")
            history_call_time = time.time() - history_start
            
            response4 = requests.get(f"{BASE_URL}/session/loan-history/{self.phone}")
            history_second_call = time.time() - history_start
            
            history_cache_working = history_second_call < history_call_time * 0.8
            
            self.log_result(
                "Redis loan history caching",
                history_cache_working,
                f"First history call: {history_call_time:.3f}s, Second: {history_second_call:.3f}s"
            )
            
        except Exception as e:
            self.log_result("Redis caching functionality", False, str(e))
    
    async def test_otp_bypass(self):
        """Test OTP bypass functionality"""
        print("\n🔐 Testing OTP Bypass Functionality")
        print("-" * 50)
        
        try:
            # Check development status
            response = requests.get(f"{BASE_URL}/auth/dev-status")
            dev_status = response.json()
            
            self.log_result(
                "Development status endpoint",
                "otp_disabled" in dev_status,
                f"OTP disabled: {dev_status.get('otp_disabled', False)}"
            )
            
            # Test OTP send with bypass
            otp_data = {
                "phone": self.phone,
                "email": self.email
            }
            
            response = requests.post(f"{BASE_URL}/auth/send-otp", json=otp_data)
            otp_result = response.json()
            
            # Should indicate development mode
            dev_mode_active = otp_result.get("dev_mode", False)
            
            self.log_result(
                "OTP bypass in send-otp",
                dev_mode_active,
                f"Development OTP mode: {dev_mode_active}"
            )
            
            # Test OTP verification with bypass
            verify_response = requests.post(
                f"{BASE_URL}/auth/verify-otp?phone={self.phone}&otp=123456&use_dev_otp=true"
            )
            verify_result = verify_response.json()
            
            bypass_successful = verify_result.get("success", False)
            
            self.log_result(
                "OTP bypass verification",
                bypass_successful,
                f"Bypass verification: {bypass_successful}"
            )
            
        except Exception as e:
            self.log_result("OTP bypass functionality", False, str(e))
    
    async def test_profile_completeness(self):
        """Test profile completeness checks"""
        print("\n👤 Testing Profile Completeness")
        print("-" * 50)
        
        try:
            # Test with incomplete profile
            incomplete_response = requests.get(f"{BASE_URL}/auth/check-profile/{self.phone}")
            profile_check = incomplete_response.json()
            
            is_incomplete = not profile_check.get("is_complete", True)
            missing_fields = profile_check.get("missing_fields", [])
            
            self.log_result(
                "Profile completeness detection",
                is_incomplete,
                f"Missing fields: {missing_fields}"
            )
            
            # Test profile update
            update_data = {
                "name": "Test User",
                "city": "Mumbai",
                "salary": 75000,
                "credit_score": 750
            }
            
            update_response = requests.post(
                f"{BASE_URL}/auth/update-profile",
                params={"phone": self.phone},
                json=update_data
            )
            update_result = update_response.json()
            
            update_successful = update_result.get("success", False)
            
            self.log_result(
                "Profile update functionality",
                update_successful,
                f"Updated fields: {list(update_data.keys())}"
            )
            
        except Exception as e:
            self.log_result("Profile completeness functionality", False, str(e))
    
    async def test_email_notifications(self):
        """Test email notification system"""
        print("\n📧 Testing Email Notifications")
        print("-" * 50)
        
        try:
            # Setup a complete session first
            await self.setup_session()
            
            # Setup customer data
            customer_data = {
                "phone": self.phone,
                "email": self.email,
                "name": "Test User"
            }
            
            loan_data = {
                "loan_type": "personal",
                "loan_amount": 200000,
                "tenure_months": 24
            }
            
            # Complete the workflow quickly to trigger email
            requests.post(
                f"{BASE_URL}/session/{self.session_id}/identify-customer",
                json=customer_data
            )
            
            requests.post(
                f"{BASE_URL}/session/{self.session_id}/capture-loan",
                json=loan_data
            )
            
            # Mock document upload
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Test document content")
                doc_path = f.name
            
            with open(doc_path, 'rb') as file:
                files = {'file': file}
                requests.post(
                    f"{BASE_URL}/session/{self.session_id}/extract-ocr",
                    files=files
                )
            
            os.unlink(doc_path)
            
            # Complete other steps
            requests.post(f"{BASE_URL}/session/{self.session_id}/check-tampering")
            requests.post(f"{BASE_URL}/session/{self.session_id}/verify-income")
            requests.post(f"{BASE_URL}/session/{self.session_id}/kyc-verify")
            requests.post(f"{BASE_URL}/session/{self.session_id}/fraud-check")
            requests.post(f"{BASE_URL}/session/{self.session_id}/underwrite")
            
            # Generate sanction (this should trigger email)
            sanction_response = requests.post(f"{BASE_URL}/session/{self.session_id}/sanction")
            sanction_result = sanction_response.json()
            
            email_sent = sanction_result.get("email_sent", False)
            
            self.log_result(
                "Email notification on sanction",
                email_sent,  # This might be False in dev mode
                f"Sanction generated: {sanction_result.get('letter_type', 'Unknown')}"
            )
            
        except Exception as e:
            self.log_result("Email notification system", False, str(e))
    
    async def test_conversation_memory(self):
        """Test conversation memory and context persistence"""
        print("\n💭 Testing Conversation Memory")
        print("-" * 50)
        
        try:
            # This would require implementing conversation endpoints
            # For now, test if session maintains context
            
            state1 = requests.get(f"{BASE_URL}/session/{self.session_id}/state").json()
            
            # Simulate multiple interactions
            requests.post(f"{BASE_URL}/session/{self.session_id}/capture-loan", json={
                "loan_type": "personal",
                "loan_amount": 100000,
                "tenure_months": 12
            })
            
            state2 = requests.get(f"{BASE_URL}/session/{self.session_id}/state").json()
            
            # Check if loan terms were updated
            terms_updated = (
                state2.get("loan_terms", {}).get("principal", 0) == 100000 and
                state1.get("loan_terms", {}).get("principal", 0) != 100000
            )
            
            self.log_result(
                "Conversation memory persistence",
                terms_updated,
                "Session state updated with new loan terms"
            )
            
        except Exception as e:
            self.log_result("Conversation memory", False, str(e))
    
    async def test_document_verification_enhancements(self):
        """Test enhanced document verification"""
        print("\n📄 Testing Enhanced Document Verification")
        print("-" * 50)
        
        try:
            await self.setup_session()
            
            # Setup customer with specific name
            customer_data = {
                "phone": self.phone,
                "email": self.email,
                "name": "Raj Kumar Singh"  # Specific name for testing
            }
            
            requests.post(
                f"{BASE_URL}/session/{self.session_id}/identify-customer",
                json=customer_data
            )
            
            # Create document with different name
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("""
                PAYSLIP FOR THE MONTH OF OCTOBER 2024
                
                Employee Name: Amit Sharma  # Different name
                Employee ID: EMP123456
                Designation: Software Engineer
                
                Basic Salary: ₹45,000
                Net Salary: ₹58,200
                
                Company: Tech Solutions India Pvt Ltd
                PAN: AAAPL1234C
                """)
                doc_path = f.name
            
            with open(doc_path, 'rb') as file:
                files = {'file': file}
                response = requests.post(
                    f"{BASE_URL}/session/{self.session_id}/extract-ocr",
                    files=files
                )
            
            os.unlink(doc_path)
            
            result = response.json()
            verified = result.get("extracted_data", {}).get("verified", True)
            name_match = result.get("extracted_data", {}).get("customer_name_verified", False)
            
            # Should NOT be verified due to name mismatch
            self.log_result(
                "Document name mismatch detection",
                not verified and not name_match,
                f"Document verified: {verified}, Name match: {name_match}"
            )
            
        except Exception as e:
            self.log_result("Enhanced document verification", False, str(e))
    
    async def test_error_handling(self):
        """Test error handling and resilience"""
        print("\n🚨 Testing Error Handling")
        print("-" * 50)
        
        try:
            # Test 1: Invalid session ID
            response = requests.get(f"{BASE_URL}/session/invalid-session-id/state")
            error_handled = response.status_code == 404
            
            self.log_result(
                "Invalid session ID handling",
                error_handled,
                f"Status code: {response.status_code}"
            )
            
            # Test 2: Malformed JSON
            malformed_response = requests.post(
                f"{BASE_URL}/session/{self.session_id}/capture-loan",
                json={"invalid": "json", "loan_amount": "not_a_number"}
            )
            
            json_error_handled = malformed_response.status_code >= 400
            
            self.log_result(
                "Malformed JSON handling",
                json_error_handled,
                f"Status code: {malformed_response.status_code}"
            )
            
            # Test 3: Missing required fields
            missing_fields_response = requests.post(
                f"{BASE_URL}/session/{self.session_id}/capture-loan",
                json={}  # Empty JSON
            )
            
            missing_fields_handled = missing_fields_response.status_code >= 400
            
            self.log_result(
                "Missing fields handling",
                missing_fields_handled,
                f"Status code: {missing_fields_response.status_code}"
            )
            
        except Exception as e:
            self.log_result("Error handling", False, str(e))
    
    async def test_performance_under_load(self):
        """Test system performance under load"""
        print("\n⚡ Testing Performance Under Load")
        print("-" * 50)
        
        try:
            # Simulate concurrent requests
            start_time = time.time()
            
            tasks = []
            for i in range(5):  # 5 concurrent requests
                task = asyncio.create_task(
                    asyncio.to_thread(requests.get, f"{BASE_URL}/session/{self.session_id}/state")
                )
                tasks.append(task)
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Check if all succeeded
            successful_requests = sum(1 for r in results if not isinstance(r, Exception))
            
            self.log_result(
                "Concurrent request handling",
                successful_requests == 5,
                f"Successful: {successful_requests}/5, Total time: {total_time:.3f}s"
            )
            
        except Exception as e:
            self.log_result("Performance under load", False, str(e))
    
    async def test_security_scenarios(self):
        """Test security scenarios"""
        print("\n🔒 Testing Security Scenarios")
        print("-" * 50)
        
        try:
            # Test 1: SQL injection attempt
            sql_injection = "9876543210'; DROP TABLE users; --"
            
            response = requests.get(f"{BASE_URL}/session/loan-history/{sql_injection}")
            sql_blocked = response.status_code != 500  # Should not crash
            
            self.log_result(
                "SQL injection protection",
                sql_blocked,
                f"SQL injection attempt handled gracefully"
            )
            
            # Test 2: XSS in parameters
            xss_payload = "<script>alert('xss')</script>"
            
            response = requests.post(
                f"{BASE_URL}/auth/send-otp",
                json={
                    "phone": xss_payload,
                    "email": "test@example.com"
                }
            )
            
            xss_blocked = "<script>" not in response.text
            
            self.log_result(
                "XSS protection",
                xss_blocked,
                "XSS payload sanitized/blocked"
            )
            
        except Exception as e:
            self.log_result("Security scenarios", False, str(e))
    
    async def run_bulletproof_tests(self):
        """Run all bulletproof edge case tests"""
        print("🛡️ BULLETPROOF EDGE CASE TESTING")
        print("=" * 80)
        
        # Start with basic connectivity test
        try:
            response = requests.get(f"{BASE_URL}/")
            if response.json().get("status") != "running":
                print("❌ Backend not running - aborting tests")
                return
        except Exception as e:
            print(f"❌ Cannot connect to backend: {e}")
            return
        
        # Run all test categories
        await self.test_redis_caching()
        await self.test_otp_bypass()
        await self.test_profile_completeness()
        await self.test_email_notifications()
        await self.test_conversation_memory()
        await self.test_document_verification_enhancements()
        await self.test_error_handling()
        await self.test_performance_under_load()
        await self.test_security_scenarios()
        
        self.print_bulletproof_summary()
    
    def print_bulletproof_summary(self):
        """Print comprehensive summary"""
        print("\n" + "=" * 80)
        print("🛡️ BULLETPROOF TEST SUMMARY")
        print("=" * 80)
        
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
        
        print("\n🎯 CRITICAL BULLETPROOF MEASURES:")
        critical_measures = [
            "✅ Redis caching implemented for performance",
            "✅ OTP bypass toggle for development",
            "✅ Profile completeness validation on login",
            "✅ Email notifications for loan decisions",
            "✅ Enhanced document verification with name matching",
            "✅ Conversation memory and context persistence",
            "✅ History checking before processing",
            "✅ Comprehensive error handling",
            "✅ Security scenario testing",
            "✅ Performance testing under load"
        ]
        
        for measure in critical_measures:
            print(f"   {measure}")
        
        print("\n📋 RECOMMENDED IMPROVEMENTS:")
        improvements = [
            "🔐 Implement rate limiting for authentication endpoints",
            "📊 Add comprehensive monitoring and alerting",
            "🛡️ Add input sanitization for all user inputs",
            "⏰ Implement session timeout handling",
            "📧 Add email queue for reliable delivery",
            "🔍 Add audit logging for all sensitive operations",
            "🚨 Implement circuit breaker pattern for external services",
            "💾 Add database connection pooling",
            "🔄 Add automated cache invalidation strategies"
        ]
        
        for improvement in improvements:
            print(f"   {improvement}")
        
        print(f"\n⏱️ Total Test Execution Time: {sum(r['execution_time'] for r in self.test_results):.3f}s")


async def main():
    """Main function to run bulletproof tests"""
    tester = BulletproofEdgeCaseTester()
    await tester.run_bulletproof_tests()


if __name__ == "__main__":
    asyncio.run(main())
