"""
Cover Letter Generator

Uses Google Gemini to generate personalized cover letters
based on user profile and job requirements.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from reportlab.lib.pagesizes import letter as letter_size
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
        output_dir: str = "output/cover_letters",
        past_letters_dir: str = "templates/past_cover_letters"
    ):
        """
        Initialize cover letter generator.
        
        Args:
            api_key: Google Gemini API key
            model: Gemini model to use
            temperature: Generation temperature
            output_dir: Directory to save generated cover letters
            past_letters_dir: Directory containing past cover letters for style learning
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.past_letters_dir = Path(past_letters_dir)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.temperature = temperature
        
        # Load and analyze past cover letters
        self.past_letters_insights = self._analyze_past_letters()
        
        logger.info(f"Initialized CoverLetterGenerator with {len(self._load_past_letters())} past letters for reference")
    
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
        
        # Include past letters style insights
        style_insights = ""
        if self.past_letters_insights:
            style_insights = f"""
## WRITING STYLE (based on candidate's past cover letters):
{self.past_letters_insights}

IMPORTANT: Write in this same style and voice. Use similar phrases and structure patterns where appropriate.
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
{style_insights}
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
                pagesize=letter_size,
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
    
    def _load_past_letters(self) -> List[Dict[str, str]]:
        """
        Load past cover letters from the configured directory.
        
        Supports .md, .txt, and .tex files.
        
        Returns:
            List of dicts with 'filename' and 'content' keys
        """
        letters = []
        
        if not self.past_letters_dir.exists():
            logger.warning(f"Past letters directory not found: {self.past_letters_dir}")
            return letters
        
        # Supported file extensions
        extensions = [".md", ".txt", ".tex"]
        
        for ext in extensions:
            for file_path in self.past_letters_dir.glob(f"*{ext}"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Clean up LaTeX files
                    if ext == ".tex":
                        content = self._clean_latex(content)
                    
                    letters.append({
                        'filename': file_path.name,
                        'content': content
                    })
                    logger.debug(f"Loaded past letter: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")
        
        return letters
    
    def _clean_latex(self, content: str) -> str:
        """
        Clean LaTeX content for readability.
        
        Removes common LaTeX commands while preserving text.
        """
        import re
        
        # Remove LaTeX preamble (everything before \begin{document})
        if r"\begin{document}" in content:
            content = content.split(r"\begin{document}")[1]
        if r"\end{document}" in content:
            content = content.split(r"\end{document}")[0]
        
        # Remove common LaTeX commands
        patterns = [
            (r'\\textbf\{([^}]+)\}', r'\1'),  # Bold
            (r'\\textit\{([^}]+)\}', r'\1'),  # Italic
            (r'\\emph\{([^}]+)\}', r'\1'),    # Emphasis
            (r'\\href\{[^}]+\}\{([^}]+)\}', r'\1'),  # Links
            (r'\\[a-zA-Z]+\{([^}]+)\}', r'\1'),  # Other commands with args
            (r'\\[a-zA-Z]+', ''),  # Commands without args
            (r'\{|\}', ''),  # Remaining braces
            (r'\\\\', '\n'),  # Line breaks
            (r'~', ' '),  # Non-breaking spaces
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Clean up extra whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    def _analyze_past_letters(self) -> str:
        """
        Analyze past cover letters to extract style insights.
        
        Returns:
            String with insights about writing style, phrases, and patterns
        """
        letters = self._load_past_letters()
        
        if not letters:
            return ""
        
        # Build analysis prompt
        letters_text = "\n\n---\n\n".join([
            f"### {item['filename']}\n{item['content'][:2000]}" 
            for item in letters[:5]  # Limit to 5 most recent
        ])
        
        analysis_prompt = f"""Analyze these cover letters written by the same person and extract:

1. WRITING STYLE: Describe the tone, formality level, and voice
2. COMMON PHRASES: List 3-5 effective phrases or expressions they often use
3. STRUCTURE PATTERNS: How do they typically organize their letters?
4. UNIQUE STRENGTHS: What makes their letters compelling?
5. KEY THEMES: What experiences/skills do they consistently highlight?

PAST COVER LETTERS:

{letters_text}

Provide a concise analysis (200 words max) that can guide writing new cover letters in the same style."""
        
        try:
            response = self.model.generate_content(
                analysis_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for analysis
                    max_output_tokens=500,
                )
            )
            insights = response.text.strip()
            logger.info("Successfully analyzed past cover letters for style insights")
            return insights
        except Exception as e:
            logger.warning(f"Failed to analyze past letters: {e}")
            return ""
    
    def get_past_letters_summary(self) -> str:
        """
        Get a summary of loaded past cover letters.
        
        Returns:
            String summarizing available past letters
        """
        letters = self._load_past_letters()
        if not letters:
            return "No past cover letters found."
        
        summary = f"Found {len(letters)} past cover letters:\n"
        for past_letter in letters:
            summary += f"  - {past_letter['filename']}\n"
        return summary
