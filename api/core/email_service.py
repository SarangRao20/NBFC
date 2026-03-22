"""Email Service for NBFC Loan System

Handles email notifications for loan submissions, approvals, rejections, and other events.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import List, Optional
from datetime import datetime
from api.config import get_settings

settings = get_settings()


class EmailService:
    """Email service for sending notifications to customers"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME
        self.connected = False
    
    async def connect(self) -> bool:
        """Connect to SMTP server"""
        if not self.smtp_user or not self.smtp_password:
            print("⚠️ Email credentials not configured")
            return False
        
        try:
            self.server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            self.server.starttls()
            self.server.login(self.smtp_user, self.smtp_password)
            self.connected = True
            print("✅ Email service connected")
            return True
        except Exception as e:
            print(f"❌ Email connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from SMTP server"""
        if self.connected and hasattr(self, 'server'):
            self.server.quit()
            self.connected = False
            print("🔌 Email service disconnected")
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        attachments: List[str] = None,
        is_html: bool = False
    ) -> bool:
        """Send email with optional attachments"""
        if not self.connected:
            if not await self.connect():
                return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Attach files if provided
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
            
            # Send email
            text = msg.as_string()
            self.server.sendmail(self.from_email, to_email, text)
            print(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Email send failed to {to_email}: {e}")
            return False
    
    async def send_loan_application_notification(
        self, 
        customer_data: dict, 
        loan_terms: dict, 
        decision: str,
        session_id: str
    ) -> bool:
        """Send loan application notification"""
        customer_name = customer_data.get('name', 'Customer')
        customer_email = customer_data.get('email', '')
        phone = customer_data.get('phone', '')
        
        if not customer_email:
            print("⚠️ No email address found for customer")
            return False
        
        # Prepare email content based on decision
        if decision == 'approve':
            subject = f"🎉 Loan Approved - FinServe NBFC - ₹{loan_terms.get('principal', 0):,}"
            body = self._get_approval_email_body(customer_name, loan_terms, session_id)
            
            # Attach sanction letter if available
            attachments = []
            sanction_pdf = f"data/sanctions/*{session_id}*.pdf"
            import glob
            pdf_files = glob.glob(sanction_pdf)
            if pdf_files:
                attachments.extend(pdf_files)
        
        elif decision in ['reject', 'soft_reject']:
            subject = f"📝 Loan Application Update - FinServe NBFC"
            body = self._get_rejection_email_body(customer_name, loan_terms, decision)
            attachments = []
            
            # Attach rejection letter if available
            rejection_pdf = f"data/sanctions/*{session_id}*Rejection*.pdf"
            pdf_files = glob.glob(rejection_pdf)
            if pdf_files:
                attachments.extend(pdf_files)
        
        else:
            subject = f"📋 Loan Application Received - FinServe NBFC"
            body = self._get_received_email_body(customer_name, loan_terms)
            attachments = []
        
        return await self.send_email(customer_email, subject, body, attachments, is_html=True)
    
    async def send_otp_email(self, customer_email: str, customer_name: str, otp: str) -> bool:
        """Send OTP verification email"""
        subject = "🔐 OTP Verification - FinServe NBFC"
        body = self._get_otp_email_body(customer_name, otp)
        return await self.send_email(customer_email, subject, body, is_html=True)
    
    async def send_profile_completion_reminder(self, customer_data: dict, missing_fields: List[str]) -> bool:
        """Send profile completion reminder"""
        customer_name = customer_data.get('name', 'Customer')
        customer_email = customer_data.get('email', '')
        
        if not customer_email:
            return False
        
        subject = "⚠️ Complete Your Profile - FinServe NBFC"
        body = self._get_profile_completion_body(customer_name, missing_fields)
        return await self.send_email(customer_email, subject, body, is_html=True)
    
    def _get_approval_email_body(self, customer_name: str, loan_terms: dict, session_id: str) -> str:
        """Generate approval email body"""
        principal = loan_terms.get('principal', 0)
        emi = loan_terms.get('emi', 0)
        tenure = loan_terms.get('tenure', 0)
        rate = loan_terms.get('rate', 0)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #28a745; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .loan-details {{ background: white; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Congratulations, {customer_name}!</h1>
                <p>Your loan has been approved by FinServe NBFC</p>
            </div>
            
            <div class="content">
                <h2>Loan Details</h2>
                <div class="loan-details">
                    <p><strong>Loan Amount:</strong> ₹{principal:,.2f}</p>
                    <p><strong>Interest Rate:</strong> {rate}% p.a.</p>
                    <p><strong>Tenure:</strong> {tenure} months</p>
                    <p><strong>Monthly EMI:</strong> ₹{emi:,.2f}</p>
                    <p><strong>Application ID:</strong> {session_id}</p>
                </div>
                
                <h3>Next Steps</h3>
                <ul>
                    <li>Complete the e-signature process</li>
                    <li>Upload required documents</li>
                    <li>Loan will be disbursed within 24-48 hours</li>
                </ul>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="#" class="btn">View Loan Details</a>
                </p>
            </div>
            
            <div class="footer">
                <p>Thank you for choosing FinServe NBFC!</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_rejection_email_body(self, customer_name: str, loan_terms: dict, decision: str) -> str:
        """Generate rejection email body"""
        principal = loan_terms.get('principal', 0)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #dc3545; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📝 Loan Application Update</h1>
                <p>Regarding your application for ₹{principal:,.2f}</p>
            </div>
            
            <div class="content">
                <h2>Dear {customer_name},</h2>
                <p>After careful consideration of your loan application, we regret to inform you that we are unable to approve your request at this time.</p>
                
                <h3>What You Can Do</h3>
                <ul>
                    <li>Check your credit score for any discrepancies</li>
                    <li>Reduce existing EMIs to improve your debt-to-income ratio</li>
                    <li>Apply again after 3 months with improved financial profile</li>
                    <li>Contact our advisory team for personalized guidance</li>
                </ul>
                
                <p>Our advisory team will contact you shortly to discuss ways to improve your eligibility for future applications.</p>
            </div>
            
            <div class="footer">
                <p>Thank you for considering FinServe NBFC!</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_received_email_body(self, customer_name: str, loan_terms: dict) -> str:
        """Generate application received email body"""
        principal = loan_terms.get('principal', 0)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 Loan Application Received</h1>
                <p>FinServe NBFC has received your application</p>
            </div>
            
            <div class="content">
                <h2>Dear {customer_name},</h2>
                <p>Thank you for applying for a loan of ₹{principal:,.2f} with FinServe NBFC.</p>
                
                <p>Your application is now being processed through our automated underwriting system. You will receive an update within 2-3 business days.</p>
                
                <h3>Application Process</h3>
                <ul>
                    <li>✅ Application received</li>
                    <li>⏳ Document verification</li>
                    <li>⏳ Credit assessment</li>
                    <li>⏳ Underwriting review</li>
                    <li>⏳ Final decision</li>
                </ul>
                
                <p>You can check your application status anytime by contacting our customer service.</p>
            </div>
            
            <div class="footer">
                <p>Thank you for choosing FinServe NBFC!</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_otp_email_body(self, customer_name: str, otp: str) -> str:
        """Generate OTP email body"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #6c757d; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .otp {{ background: #e9ecef; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0; border-radius: 5px; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔐 OTP Verification</h1>
                <p>FinServe NBFC - One-Time Password</p>
            </div>
            
            <div class="content">
                <h2>Dear {customer_name},</h2>
                <p>Your One-Time Password (OTP) for login is:</p>
                
                <div class="otp">{otp}</div>
                
                <p><strong>Important:</strong></p>
                <ul>
                    <li>This OTP is valid for 5 minutes only</li>
                    <li>Please do not share this OTP with anyone</li>
                    <li>FinServe NBFC will never ask for your OTP</li>
                </ul>
                
                <p>If you didn't request this OTP, please contact our customer service immediately.</p>
            </div>
            
            <div class="footer">
                <p>Thank you for using FinServe NBFC!</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_profile_completion_body(self, customer_name: str, missing_fields: List[str]) -> str:
        """Generate profile completion email body"""
        fields_list = "\n".join([f"• {field.replace('_', ' ').title()}" for field in missing_fields])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #ffc107; color: #000; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .missing-fields {{ background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⚠️ Complete Your Profile</h1>
                <p>FinServe NBFC - Action Required</p>
            </div>
            
            <div class="content">
                <h2>Dear {customer_name},</h2>
                <p>To continue with your loan application, please complete the following missing information in your profile:</p>
                
                <div class="missing-fields">
                    <h3>Missing Information:</h3>
                    {fields_list}
                </div>
                
                <p>Having complete information helps us:</p>
                <ul>
                    <li>Process your application faster</li>
                    <li>Provide better loan offers</li>
                    <li>Ensure accurate risk assessment</li>
                </ul>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="#" class="btn">Complete Profile Now</a>
                </p>
            </div>
            
            <div class="footer">
                <p>Thank you for choosing FinServe NBFC!</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """

# Global email service instance
email_service = EmailService()


async def get_email_service() -> EmailService:
    """Get the global email service instance"""
    return email_service
