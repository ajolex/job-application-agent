"""
Cover Letter Generator

Uses Google Gemini to generate personalized cover letters
based on user profile and job requirements.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from src.database.db_manager import Job
from src.matching.matcher import MatchScore

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """
    Generates personalized cover letters using Gemini AI.
    
    Creates tailored cover letters that highlight relevant
    experience and skills for each job.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.7,
        output_dir: str = "output/cover_letters"
    ):
        """
        Initialize cover letter generator.
        
        Args:
            api_key: Google Gemini API key
            model: Gemini model to use
            temperature: Generation temperature
            output_dir: Directory to save generated cover letters
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.temperature = temperature
        
        logger.info(f"Initialized CoverLetterGenerator")
    
    def generate(
        self,
        job: Job,
        profile: Dict[str, Any],
        match_score: Optional[MatchScore] = None,
        template: Optional[str] = None
    ) -> str:
        """
        Generate a cover letter for a specific job.
        
        Args:
            job: Job posting
            profile: User profile dictionary
            match_score: Optional match score with insights
            template: Optional custom template
            
        Returns:
            Generated cover letter text
        """
        prompt = self._build_generation_prompt(job, profile, match_score, template)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=2048,
                )
            )
            
            cover_letter = response.text.strip()
            logger.info(f"Generated cover letter for {job.title} at {job.organization}")
            return cover_letter
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            raise
    
    def generate_and_save(
        self,
        job: Job,
        profile: Dict[str, Any],
        match_score: Optional[MatchScore] = None,
        template: Optional[str] = None,
        save_pdf: bool = True,
        save_txt: bool = True
    ) -> Dict[str, str]:
        """
        Generate cover letter and save to files.
        
        Args:
            job: Job posting
            profile: User profile dictionary
            match_score: Optional match score
            template: Optional custom template
            save_pdf: Save as PDF
            save_txt: Save as text file
            
        Returns:
            Dictionary with file paths
        """
        cover_letter = self.generate(job, profile, match_score, template)
        
        # Generate filename
        safe_org = "".join(c if c.isalnum() else "_" for c in job.organization)[:30]
        safe_title = "".join(c if c.isalnum() else "_" for c in job.title)[:30]
        timestamp = datetime.now().strftime("%Y%m%d")
        base_filename = f"cover_letter_{safe_org}_{safe_title}_{timestamp}"
        
        paths = {}
        
        # Save text file
        if save_txt:
            txt_path = self.output_dir / f"{base_filename}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)
            paths["txt"] = str(txt_path)
            logger.debug(f"Saved cover letter to {txt_path}")
        
        # Save PDF
        if save_pdf:
            pdf_path = self.output_dir / f"{base_filename}.pdf"
            self._save_as_pdf(cover_letter, pdf_path, profile.get("name", ""))
            paths["pdf"] = str(pdf_path)
            logger.debug(f"Saved cover letter PDF to {pdf_path}")
        
        return paths
    
    def _build_generation_prompt(
        self,
        job: Job,
        profile: Dict[str, Any],
        match_score: Optional[MatchScore],
        template: Optional[str]
    ) -> str:
        """Build the prompt for cover letter generation."""
        
        # Include match insights if available
        match_insights = ""
        if match_score:
            match_insights = f"""
## MATCH ANALYSIS (use these insights):
- Key Strengths: {', '.join(match_score.highlights[:3]) if match_score.highlights else 'General alignment'}
- Areas to Address: {', '.join(match_score.concerns[:2]) if match_score.concerns else 'None critical'}
- Match Reasoning: {match_score.reasoning}
"""
        
        template_instruction = ""
        if template:
            template_instruction = f"""
## TEMPLATE TO FOLLOW:
{template}

Adapt this template structure while personalizing the content.
"""
        
        return f"""You are an expert career advisor helping a Development Economics professional write a compelling cover letter.

## CANDIDATE PROFILE:
Name: {profile.get('name', '[Name]')}
Email: {profile.get('email', '')}
Summary: {profile.get('summary', '')}
Skills: {', '.join(profile.get('skills', []))}
Education: {profile.get('education', '')}
Experience: {profile.get('experience', '')}
Research Interests: {', '.join(profile.get('research_interests', []))}

## JOB POSTING:
Title: {job.title}
Organization: {job.organization}
Location: {job.location}
Description: {job.description[:2500] if job.description else 'Not provided'}
Requirements: {job.requirements[:1000] if job.requirements else 'Not provided'}
{match_insights}
{template_instruction}

## INSTRUCTIONS:
Write a professional, personalized cover letter (300-400 words) that:

1. Opens with a compelling hook mentioning the specific role and organization
2. Highlights 2-3 most relevant experiences/skills that match the job requirements
3. Demonstrates knowledge of the organization's work and mission
4. Shows enthusiasm for the role and how it aligns with career goals
5. Concludes with a confident call to action

Style Guidelines:
- Professional but personable tone
- Specific examples over generic claims
- Focus on Development Economics, research, and analytical skills
- No clichés or overly formal language
- Show, don't tell

Format the letter professionally with:
- Today's date
- Proper salutation (Dear Hiring Manager if no specific name)
- Clear paragraphs
- Professional closing

Write ONLY the cover letter, no additional commentary."""
    
    def _save_as_pdf(self, content: str, output_path: Path, name: str) -> None:
        """Save cover letter as PDF using ReportLab."""
        try:
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=inch,
                leftMargin=inch,
                topMargin=inch,
                bottomMargin=inch
            )
            
            styles = getSampleStyleSheet()
            
            # Custom style for body text
            body_style = ParagraphStyle(
                'Body',
                parent=styles['Normal'],
                fontSize=11,
                leading=14,
                spaceAfter=12,
            )
            
            # Build content
            story = []
            
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    # Handle line breaks within paragraphs
                    para = para.replace('\n', '<br/>')
                    story.append(Paragraph(para, body_style))
                    story.append(Spacer(1, 6))
            
            doc.build(story)
            
        except Exception as e:
            logger.error(f"Failed to create PDF: {e}")
            # Fall back to saving as text if PDF fails
            output_path = output_path.with_suffix('.txt')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def load_template(self, template_path: str) -> str:
        """Load a cover letter template from file."""
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
