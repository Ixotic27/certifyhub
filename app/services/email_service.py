"""
Email Service
Handle sending emails to admins
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import asyncio


class EmailService:
    """Service for sending emails"""
    
    @staticmethod
    async def send_welcome_email(
        admin_email: str,
        admin_name: str,
        club_name: str,
        temp_password: str
    ) -> bool:
        """
        Send welcome email to new club admin
        
        Args:
            admin_email: Recipient email
            admin_name: Admin full name
            club_name: Club name
            temp_password: Generated temporary password
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = f"Welcome to CertifyHub - {club_name}"
            message["From"] = settings.EMAIL_FROM
            message["To"] = admin_email
            
            # HTML email body
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #2c3e50;">Welcome to CertifyHub!</h2>
                  
                  <p>Hi {admin_name},</p>
                  
                  <p>You have been added as an administrator for <strong>{club_name}</strong> on CertifyHub.</p>
                  
                  <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                    <p><strong>Your Login Credentials:</strong></p>
                    <p>Email: <code>{admin_email}</code></p>
                    <p>Password: <code>{temp_password}</code></p>
                  </div>
                  
                  <p style="color: #e74c3c;"><strong>IMPORTANT:</strong> You must change this password on your first login.</p>
                  
                  <p>
                    <a href="{settings.APP_URL}/admin/login" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                      Login to CertifyHub
                    </a>
                  </p>
                  
                  <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                  
                  <p><strong>What You Can Do:</strong></p>
                  <ul>
                    <li>Upload certificate templates</li>
                    <li>Configure text field coordinates</li>
                    <li>Upload attendee lists (CSV)</li>
                    <li>View certificate statistics</li>
                    <li>Manage club settings</li>
                  </ul>
                  
                  <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                  
                  <p>If you have any questions, please reply to this email.</p>
                  
                  <p>Best regards,<br><strong>CertifyHub Team</strong></p>
                </div>
              </body>
            </html>
            """
            
            # Text version for fallback
            text_body = f"""
Welcome to CertifyHub!

Hi {admin_name},

You have been added as an administrator for {club_name} on CertifyHub.

Your Login Credentials:
Email: {admin_email}
Password: {temp_password}

IMPORTANT: You must change this password on your first login.

Login here: {settings.APP_URL}/admin/login

What You Can Do:
- Upload certificate templates
- Configure text field coordinates
- Upload attendee lists (CSV)
- View certificate statistics
- Manage club settings

If you have any questions, please reply to this email.

Best regards,
CertifyHub Team
            """
            
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            
            message.attach(part1)
            message.attach(part2)
            
            # Send email (in development, just log it)
            if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
                try:
                    async with aiosmtplib.SMTP(hostname=settings.SMTP_HOST, port=settings.SMTP_PORT) as smtp:
                        await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                        await smtp.sendmail(settings.EMAIL_FROM, admin_email, message.as_string())
                        return True
                except Exception as e:
                    # In development, log but don't fail
                    print(f"Warning: Email send failed (development mode): {e}")
                    print(f"Email would have been sent to: {admin_email}")
                    print(f"Subject: {message['Subject']}")
                    return False
            else:
                # Development mode - no SMTP configured
                print(f"\n--- EMAIL (Development Mode) ---")
                print(f"To: {admin_email}")
                print(f"Subject: {message['Subject']}")
                print(f"Body:\n{html_body}")
                print(f"--- END EMAIL ---\n")
                return True
                
        except Exception as e:
            print(f"Error sending email: {e}")
            return False


# Create singleton instance
email_service = EmailService()
