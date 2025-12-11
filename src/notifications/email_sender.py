"""
Email Notification System

Sends job match notifications via Gmail API with
attachments for cover letters and CV.
"""

import base64
import logging
import mimetypes
import os
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.database.db_manager import Job
from src.matching.matcher import MatchScore

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class EmailSender:
    """
    Sends email notifications via Gmail API.
    
    Supports HTML emails with attachments for cover letters and CVs.
    """
    
    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
        sender_email: Optional[str] = None
    ):
        """
        Initialize email sender.
        
        Args:
            credentials_path: Path to Gmail API credentials JSON
            token_path: Path to store OAuth token
            sender_email: Sender email address
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.sender_email = sender_email
        self.service = None
        
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with Gmail API."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {self.credentials_path}. "
                        "Please set up OAuth credentials in Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save the token
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API authenticated successfully")
    
    def send_job_summary(
        self,
        recipient: str,
        matched_jobs: List[tuple],
        cv_path: Optional[str] = None,
        include_cover_letters: bool = False  # Changed default to False
    ) -> bool:
        """
        Send daily summary email with matched jobs.
        
        Args:
            recipient: Email recipient
            matched_jobs: List of (Job, MatchScore) tuples
            cv_path: Optional path to CV file
            include_cover_letters: Whether to attach cover letters (default False)
            
        Returns:
            True if sent successfully
        """
        if not matched_jobs:
            logger.info("No matched jobs to send")
            return False
        
        # Build email content - compact summary format
        subject = f"🎯 Job Matches Found - {datetime.now().strftime('%B %d, %Y')} ({len(matched_jobs)} jobs)"
        
        html_content = self._build_summary_html(matched_jobs)
        text_content = self._build_summary_text(matched_jobs)
        
        # No attachments by default - cover letters saved locally as .md files
        attachments = []
        
        if cv_path and os.path.exists(cv_path):
            attachments.append(cv_path)
        
        return self.send_email(
            recipient=recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            attachments=attachments
        )
    
    def send_email(
        self,
        recipient: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email via Gmail API.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body (fallback)
            attachments: List of file paths to attach
            
        Returns:
            True if sent successfully
        """
        try:
            message = MIMEMultipart('mixed')
            message['to'] = recipient
            message['from'] = self.sender_email or 'me'
            message['subject'] = subject
            
            # Create body part
            body = MIMEMultipart('alternative')
            
            if text_content:
                body.attach(MIMEText(text_content, 'plain'))
            
            body.attach(MIMEText(html_content, 'html'))
            message.attach(body)
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        attachment = self._create_attachment(file_path)
                        if attachment:
                            message.attach(attachment)
            
            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _create_attachment(self, file_path: str) -> Optional[MIMEBase]:
        """Create an email attachment from file."""
        try:
            filename = os.path.basename(file_path)
            content_type, _ = mimetypes.guess_type(file_path)
            
            if content_type is None:
                content_type = 'application/octet-stream'
            
            main_type, sub_type = content_type.split('/', 1)
            
            with open(file_path, 'rb') as f:
                attachment = MIMEBase(main_type, sub_type)
                attachment.set_payload(f.read())
            
            from email import encoders
            encoders.encode_base64(attachment)
            
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=filename
            )
            
            return attachment
            
        except Exception as e:
            logger.warning(f"Failed to create attachment {file_path}: {e}")
            return None
    
    def _build_summary_html(self, matched_jobs: List[tuple]) -> str:
        """Build compact HTML content for summary email."""
        jobs_html = ""
        
        for i, (job, score) in enumerate(matched_jobs, 1):
            generated_date = datetime.now().strftime('%Y-%m-%d')
            job_url = job.application_url or job.url
            
            jobs_html += f"""
            <div style="margin-bottom: 15px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #fafafa;">
                <h3 style="margin: 0 0 10px 0; color: #1a73e8;">
                    {i}. {job.title}
                </h3>
                <table style="width: 100%; font-size: 14px; color: #3c4043;">
                    <tr><td style="padding: 4px 0;"><strong>Organization:</strong></td><td>{job.organization}</td></tr>
                    <tr><td style="padding: 4px 0;"><strong>Location:</strong></td><td>{job.location or 'Not specified'}</td></tr>
                    <tr><td style="padding: 4px 0;"><strong>Generated:</strong></td><td>{generated_date}</td></tr>
                    <tr><td style="padding: 4px 0;"><strong>Job URL:</strong></td><td><a href="{job_url}" style="color: #1a73e8;">{job_url}</a></td></tr>
                </table>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #202124; max-width: 700px; margin: 0 auto; padding: 20px; }}
                h2 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
            </style>
        </head>
        <body>
            <h2>🎯 Job Application Agent - Daily Summary</h2>
            <p>Found <strong>{len(matched_jobs)}</strong> positions matching your profile. Cover letters have been generated and saved locally.</p>
            
            {jobs_html}
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #e0e0e0;">
            
            <p style="color: #5f6368; font-size: 12px;">
                This email was sent by Job Application Agent.<br>
                Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}
            </p>
        </body>
        </html>
        """
    
    def _build_summary_text(self, matched_jobs: List[tuple]) -> str:
        """Build plain text content for summary email."""
        text = f"Job Application Agent - Daily Summary\n"
        text += f"{datetime.now().strftime('%B %d, %Y')}\n"
        text += f"Found {len(matched_jobs)} positions matching your profile.\n"
        text += "Cover letters have been generated and saved locally.\n\n"
        text += "=" * 50 + "\n\n"
        
        generated_date = datetime.now().strftime('%Y-%m-%d')
        
        for i, (job, score) in enumerate(matched_jobs, 1):
            job_url = job.application_url or job.url
            text += f"{i}. {job.title}\n"
            text += f"   Organization: {job.organization}\n"
            text += f"   Location: {job.location or 'Not specified'}\n"
            text += f"   Generated: {generated_date}\n"
            text += f"   Job URL: {job_url}\n\n"
        
        return text
