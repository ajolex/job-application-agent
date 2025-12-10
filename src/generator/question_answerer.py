"""
Application Question Answerer

Uses Google Gemini to generate personalized answers to
job application questions based on user profile.
"""

import logging
from typing import Dict, Any, List, Optional

import google.generativeai as genai

from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class QuestionAnswerer:
    """
    Generates personalized answers to application questions.
    
    Uses AI to craft relevant, professional responses based on
    the user's profile and job context.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.6
    ):
        """
        Initialize question answerer.
        
        Args:
            api_key: Google Gemini API key
            model: Gemini model to use
            temperature: Generation temperature
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.temperature = temperature
        
        logger.info("Initialized QuestionAnswerer")
    
    def answer_question(
        self,
        question: str,
        profile: Dict[str, Any],
        job: Optional[Job] = None,
        max_words: Optional[int] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate an answer to an application question.
        
        Args:
            question: The question to answer
            profile: User profile dictionary
            job: Optional job context
            max_words: Optional word limit
            context: Optional additional context
            
        Returns:
            Generated answer
        """
        prompt = self._build_answer_prompt(question, profile, job, max_words, context)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=1024,
                )
            )
            
            answer = response.text.strip()
            logger.info(f"Generated answer for question: {question[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise
    
    def answer_questions(
        self,
        questions: List[Dict[str, Any]],
        profile: Dict[str, Any],
        job: Optional[Job] = None
    ) -> List[Dict[str, str]]:
        """
        Generate answers to multiple application questions.
        
        Args:
            questions: List of question dictionaries with 'question' and optional 'max_words' keys
            profile: User profile dictionary
            job: Optional job context
            
        Returns:
            List of dictionaries with 'question' and 'answer' keys
        """
        results = []
        
        for q in questions:
            question = q.get("question", "")
            max_words = q.get("max_words")
            context = q.get("context")
            
            answer = self.answer_question(
                question=question,
                profile=profile,
                job=job,
                max_words=max_words,
                context=context
            )
            
            results.append({
                "question": question,
                "answer": answer
            })
        
        return results
    
    def _build_answer_prompt(
        self,
        question: str,
        profile: Dict[str, Any],
        job: Optional[Job],
        max_words: Optional[int],
        context: Optional[str]
    ) -> str:
        """Build the prompt for answer generation."""
        
        job_context = ""
        if job:
            job_context = f"""
## JOB CONTEXT:
Title: {job.title}
Organization: {job.organization}
Description: {job.description[:1500] if job.description else 'Not provided'}
"""
        
        additional_context = ""
        if context:
            additional_context = f"""
## ADDITIONAL CONTEXT:
{context}
"""
        
        word_limit = ""
        if max_words:
            word_limit = f"\n**Word Limit: {max_words} words maximum**"
        
        return f"""You are an expert career advisor helping a Development Economics professional answer application questions.

## CANDIDATE PROFILE:
Name: {profile.get('name', 'Candidate')}
Summary: {profile.get('summary', '')}
Skills: {', '.join(profile.get('skills', []))}
Education: {profile.get('education', '')}
Experience: {profile.get('experience', '')}
Research Interests: {', '.join(profile.get('research_interests', []))}
{job_context}
{additional_context}

## APPLICATION QUESTION:
{question}
{word_limit}

## INSTRUCTIONS:
Write a compelling, professional answer that:

1. Directly addresses the question
2. Uses specific examples from the candidate's background
3. Demonstrates relevant skills and experience
4. Shows enthusiasm and fit for the role
5. Is honest and authentic in tone

Guidelines:
- Be specific, not generic
- Use the STAR method (Situation, Task, Action, Result) for behavioral questions
- Quantify achievements where possible
- Focus on Development Economics and research experience
- Match the tone to the organization (e.g., more formal for UN, slightly less for NGOs)

Write ONLY the answer, no additional commentary or formatting."""
    
    def suggest_questions(self, job: Job) -> List[str]:
        """
        Suggest common application questions based on job type.
        
        Args:
            job: Job posting
            
        Returns:
            List of likely application questions
        """
        # Common questions for development economics roles
        common_questions = [
            "Why are you interested in this position?",
            "Describe your experience with impact evaluation or research methodology.",
            "How does your background align with our organization's mission?",
            "Describe a challenging research project you've worked on and how you overcame obstacles.",
            "What is your experience working with data analysis tools (Stata, R, Python)?",
            "Tell us about your experience working in developing countries or cross-cultural settings.",
            "How do you prioritize tasks when managing multiple projects?",
            "Describe your experience with policy-relevant research.",
        ]
        
        # Add role-specific questions based on job content
        description_lower = (job.description or "").lower()
        
        if "management" in description_lower or "lead" in description_lower:
            common_questions.extend([
                "Describe your experience managing a team or project.",
                "How do you handle conflicts within a team?",
            ])
        
        if "field" in description_lower or "survey" in description_lower:
            common_questions.extend([
                "Describe your experience with field research or data collection.",
                "How do you ensure data quality in field settings?",
            ])
        
        if "publication" in description_lower or "writing" in description_lower:
            common_questions.extend([
                "Describe your publication experience or a paper you've contributed to.",
                "How do you communicate complex research findings to non-technical audiences?",
            ])
        
        return common_questions[:8]  # Return top 8 most relevant
