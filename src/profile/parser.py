"""
Profile Parser for Job Application Agent.

Parses user's HTML profile/CV to extract skills, experience,
education, research interests, and publications.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class Education:
    """Educational qualification."""
    degree: str
    institution: str
    field: str = ""
    year: str = ""
    details: str = ""


@dataclass
class Experience:
    """Work experience entry."""
    title: str
    organization: str
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    description: str = ""
    highlights: List[str] = field(default_factory=list)


@dataclass
class Publication:
    """Publication entry."""
    title: str
    authors: str = ""
    venue: str = ""
    year: str = ""
    url: str = ""
    abstract: str = ""


@dataclass
class UserProfile:
    """
    Complete user profile extracted from CV/website.
    
    This is the main data structure used for job matching
    and cover letter generation.
    """
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    website: str = ""
    linkedin: str = ""
    github: str = ""
    
    # Professional summary
    summary: str = ""
    
    # Core competencies
    skills: List[str] = field(default_factory=list)
    technical_skills: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    
    # Experience and education
    education: List[Education] = field(default_factory=list)
    experience: List[Experience] = field(default_factory=list)
    
    # Research
    research_interests: List[str] = field(default_factory=list)
    publications: List[Publication] = field(default_factory=list)
    
    # Additional
    certifications: List[str] = field(default_factory=list)
    awards: List[str] = field(default_factory=list)
    
    # Metadata
    source_path: str = ""
    parsed_date: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        data = asdict(self)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Create profile from dictionary."""
        # Convert nested dataclasses
        education = [Education(**e) if isinstance(e, dict) else e for e in data.get("education", [])]
        experience = [Experience(**e) if isinstance(e, dict) else e for e in data.get("experience", [])]
        publications = [Publication(**p) if isinstance(p, dict) else p for p in data.get("publications", [])]
        
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location", ""),
            website=data.get("website", ""),
            linkedin=data.get("linkedin", ""),
            github=data.get("github", ""),
            summary=data.get("summary", ""),
            skills=data.get("skills", []),
            technical_skills=data.get("technical_skills", []),
            languages=data.get("languages", []),
            tools=data.get("tools", []),
            education=education,
            experience=experience,
            research_interests=data.get("research_interests", []),
            publications=publications,
            certifications=data.get("certifications", []),
            awards=data.get("awards", []),
            source_path=data.get("source_path", ""),
            parsed_date=data.get("parsed_date", "")
        )
    
    def get_all_skills(self) -> List[str]:
        """Get all skills combined."""
        all_skills = set(self.skills)
        all_skills.update(self.technical_skills)
        all_skills.update(self.tools)
        return list(all_skills)
    
    def get_experience_summary(self) -> str:
        """Get a summary of work experience."""
        if not self.experience:
            return ""
        
        summaries = []
        for exp in self.experience:
            summary = f"{exp.title} at {exp.organization}"
            if exp.start_date:
                summary += f" ({exp.start_date}"
                if exp.end_date:
                    summary += f" - {exp.end_date}"
                summary += ")"
            summaries.append(summary)
        
        return "; ".join(summaries)
    
    def get_education_summary(self) -> str:
        """Get a summary of education."""
        if not self.education:
            return ""
        
        summaries = []
        for edu in self.education:
            summary = f"{edu.degree}"
            if edu.field:
                summary += f" in {edu.field}"
            summary += f" from {edu.institution}"
            if edu.year:
                summary += f" ({edu.year})"
            summaries.append(summary)
        
        return "; ".join(summaries)


class ProfileParser:
    """
    Parses user profile from HTML file.
    
    Supports various HTML structures commonly used in personal websites
    and online CV/resume pages.
    """
    
    def __init__(self, cache_path: str = "data/profile_cache.json", cache_duration_hours: int = 24):
        """
        Initialize profile parser.
        
        Args:
            cache_path: Path to cache file
            cache_duration_hours: How long to cache parsed profile
        """
        self.cache_path = Path(cache_path)
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.profile: Optional[UserProfile] = None
    
    def parse(self, html_path: str, force_refresh: bool = False) -> UserProfile:
        """
        Parse profile from HTML file.
        
        Args:
            html_path: Path to HTML file
            force_refresh: If True, ignore cache and re-parse
            
        Returns:
            UserProfile object
        """
        html_path = Path(html_path)
        
        # Check cache first
        if not force_refresh:
            cached = self._load_from_cache(str(html_path))
            if cached:
                logger.info(f"Loaded profile from cache")
                self.profile = cached
                return cached
        
        # Parse HTML file
        logger.info(f"Parsing profile from {html_path}")
        
        if not html_path.exists():
            raise FileNotFoundError(f"Profile HTML not found: {html_path}")
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, "lxml")
        
        # Extract profile data
        profile = UserProfile(
            source_path=str(html_path),
            parsed_date=datetime.now().isoformat()
        )
        
        # Extract different sections
        self._extract_contact_info(soup, profile)
        self._extract_summary(soup, profile)
        self._extract_skills(soup, profile)
        self._extract_education(soup, profile)
        self._extract_experience(soup, profile)
        self._extract_research(soup, profile)
        self._extract_publications(soup, profile)
        
        # Cache the profile
        self._save_to_cache(profile)
        
        self.profile = profile
        logger.info(f"Successfully parsed profile for {profile.name}")
        
        return profile
    
    def _extract_contact_info(self, soup: BeautifulSoup, profile: UserProfile) -> None:
        """Extract contact information."""
        # Try to find name from various common patterns
        name_selectors = [
            "h1.name", ".name h1", "#name", ".profile-name",
            "h1:first-of-type", ".header h1", "#header h1"
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                profile.name = element.get_text(strip=True)
                break
        
        # If no name found, try meta tags or title
        if not profile.name:
            meta_author = soup.find("meta", {"name": "author"})
            if meta_author and meta_author.get("content"):
                profile.name = meta_author["content"]
            elif soup.title:
                profile.name = soup.title.get_text(strip=True).split("|")[0].strip()
        
        # Extract email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_link = soup.find("a", href=re.compile(r"^mailto:"))
        if email_link:
            profile.email = email_link["href"].replace("mailto:", "").split("?")[0]
        else:
            # Search in text
            text = soup.get_text()
            emails = re.findall(email_pattern, text)
            if emails:
                profile.email = emails[0]
        
        # Extract LinkedIn
        linkedin_link = soup.find("a", href=re.compile(r"linkedin\.com"))
        if linkedin_link:
            profile.linkedin = linkedin_link["href"]
        
        # Extract GitHub
        github_link = soup.find("a", href=re.compile(r"github\.com"))
        if github_link:
            profile.github = github_link["href"]
        
        # Extract location
        location_selectors = [".location", "#location", ".address", ".contact-location"]
        for selector in location_selectors:
            element = soup.select_one(selector)
            if element:
                profile.location = element.get_text(strip=True)
                break
    
    def _extract_summary(self, soup: BeautifulSoup, profile: UserProfile) -> None:
        """Extract professional summary/about section."""
        summary_selectors = [
            "#about", ".about", "#summary", ".summary",
            "#bio", ".bio", ".profile-summary", "#profile",
            "section.about", "div.about-me"
        ]
        
        for selector in summary_selectors:
            element = soup.select_one(selector)
            if element:
                # Get text, excluding headers
                for header in element.find_all(["h1", "h2", "h3", "h4"]):
                    header.decompose()
                profile.summary = element.get_text(separator=" ", strip=True)
                break
        
        # Also look for common header patterns
        if not profile.summary:
            for header in soup.find_all(["h2", "h3"]):
                header_text = header.get_text(strip=True).lower()
                if any(keyword in header_text for keyword in ["about", "summary", "bio", "profile"]):
                    # Get the next sibling content
                    content = []
                    for sibling in header.find_next_siblings():
                        if sibling.name in ["h2", "h3", "h4"]:
                            break
                        content.append(sibling.get_text(separator=" ", strip=True))
                    if content:
                        profile.summary = " ".join(content)
                        break
    
    def _extract_skills(self, soup: BeautifulSoup, profile: UserProfile) -> None:
        """Extract skills and competencies."""
        skills_selectors = [
            "#skills", ".skills", "#competencies", ".competencies",
            "section.skills", ".skill-list", "#technical-skills"
        ]
        
        all_skills = []
        
        for selector in skills_selectors:
            element = soup.select_one(selector)
            if element:
                # Look for list items
                for li in element.find_all("li"):
                    skill = li.get_text(strip=True)
                    if skill and len(skill) < 100:  # Reasonable skill length
                        all_skills.append(skill)
                
                # Look for tags/badges
                for tag in element.find_all(class_=re.compile(r"tag|badge|skill-item|chip")):
                    skill = tag.get_text(strip=True)
                    if skill and len(skill) < 100:
                        all_skills.append(skill)
        
        # Also look for skills section by header
        for header in soup.find_all(["h2", "h3", "h4"]):
            header_text = header.get_text(strip=True).lower()
            if any(keyword in header_text for keyword in ["skill", "competenc", "expertise", "technologies"]):
                # Get content from next elements
                for sibling in header.find_next_siblings():
                    if sibling.name in ["h2", "h3"]:
                        break
                    for li in sibling.find_all("li"):
                        skill = li.get_text(strip=True)
                        if skill and len(skill) < 100:
                            all_skills.append(skill)
                    
                    # Also check for comma-separated skills in paragraphs
                    if sibling.name == "p":
                        text = sibling.get_text(strip=True)
                        # Split by common separators
                        potential_skills = re.split(r'[,;|•]', text)
                        for skill in potential_skills:
                            skill = skill.strip()
                            if skill and len(skill) < 50:
                                all_skills.append(skill)
        
        # Deduplicate and categorize
        seen = set()
        technical_keywords = ["python", "r", "stata", "sql", "matlab", "excel", "spss", "sas", 
                            "javascript", "java", "c++", "tableau", "power bi", "gis", "arcgis",
                            "machine learning", "data analysis", "econometrics", "statistics"]
        
        for skill in all_skills:
            skill_lower = skill.lower()
            if skill_lower not in seen:
                seen.add(skill_lower)
                if any(tech in skill_lower for tech in technical_keywords):
                    profile.technical_skills.append(skill)
                else:
                    profile.skills.append(skill)
    
    def _extract_education(self, soup: BeautifulSoup, profile: UserProfile) -> None:
        """Extract education history."""
        education_selectors = [
            "#education", ".education", "section.education",
            "#academic", ".academic-background"
        ]
        
        education_items = []
        
        # Find education section
        for selector in education_selectors:
            element = soup.select_one(selector)
            if element:
                education_items = self._parse_education_section(element)
                break
        
        # Also search by header
        if not education_items:
            for header in soup.find_all(["h2", "h3"]):
                header_text = header.get_text(strip=True).lower()
                if "education" in header_text or "academic" in header_text:
                    # Get sibling content
                    container = header.find_parent(["section", "div", "article"])
                    if container:
                        education_items = self._parse_education_section(container)
                    break
        
        profile.education = education_items
    
    def _parse_education_section(self, element: Any) -> List[Education]:
        """Parse education items from a section."""
        education_items = []
        
        # Look for individual education entries
        for entry in element.find_all(class_=re.compile(r"education-item|edu-entry|degree|qualification")):
            edu = self._parse_education_entry(entry)
            if edu:
                education_items.append(edu)
        
        # Also try list items
        for li in element.find_all("li"):
            # Check if this looks like an education entry
            text = li.get_text(strip=True)
            if any(keyword in text.lower() for keyword in ["bachelor", "master", "phd", "msc", "bsc", "ba", "ma", "mba", "doctorate"]):
                edu = self._parse_education_entry(li)
                if edu:
                    education_items.append(edu)
        
        return education_items
    
    def _parse_education_entry(self, element: Any) -> Optional[Education]:
        """Parse a single education entry."""
        text = element.get_text(separator=" ", strip=True)
        
        # Common degree patterns
        degree_patterns = [
            r"(Ph\.?D\.?|Doctor(?:ate)?|DPhil)",
            r"(M\.?(?:Sc|A|S|Phil|Econ|BA|PA|PP)\.?|Master(?:'s)?)",
            r"(B\.?(?:Sc|A|S|Econ|BA)\.?|Bachelor(?:'s)?)",
            r"(MBA|MPA|MPP)",
        ]
        
        degree = ""
        for pattern in degree_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                degree = match.group(1)
                break
        
        if not degree:
            # Try to find degree from text structure
            parts = text.split(",")
            if parts:
                degree = parts[0].strip()
        
        # Try to find institution
        institution = ""
        # Look for common university keywords
        institution_pattern = r"(?:at\s+|from\s+|,\s*)?([A-Z][^,\d]+(?:University|College|Institute|School)[^,\d]*)"
        inst_match = re.search(institution_pattern, text)
        if inst_match:
            institution = inst_match.group(1).strip()
        
        # Try to find year
        year = ""
        year_match = re.search(r"(19|20)\d{2}", text)
        if year_match:
            year = year_match.group(0)
        
        if degree or institution:
            return Education(
                degree=degree,
                institution=institution,
                year=year,
                details=text
            )
        
        return None
    
    def _extract_experience(self, soup: BeautifulSoup, profile: UserProfile) -> None:
        """Extract work experience."""
        experience_selectors = [
            "#experience", ".experience", "#work-experience", ".work-experience",
            "section.experience", "#employment", ".employment"
        ]
        
        experience_items = []
        
        # Find experience section
        for selector in experience_selectors:
            element = soup.select_one(selector)
            if element:
                experience_items = self._parse_experience_section(element)
                break
        
        # Also search by header
        if not experience_items:
            for header in soup.find_all(["h2", "h3"]):
                header_text = header.get_text(strip=True).lower()
                if any(keyword in header_text for keyword in ["experience", "employment", "work history", "professional"]):
                    container = header.find_parent(["section", "div", "article"])
                    if container:
                        experience_items = self._parse_experience_section(container)
                    break
        
        profile.experience = experience_items
    
    def _parse_experience_section(self, element: Any) -> List[Experience]:
        """Parse experience items from a section."""
        experience_items = []
        
        # Look for individual experience entries
        for entry in element.find_all(class_=re.compile(r"experience-item|job|position|role|work-item")):
            exp = self._parse_experience_entry(entry)
            if exp:
                experience_items.append(exp)
        
        # Also try to find by structure (h3/h4 followed by content)
        for header in element.find_all(["h3", "h4", "h5"]):
            # This might be a job title or organization
            title_text = header.get_text(strip=True)
            
            # Skip section headers
            if any(keyword in title_text.lower() for keyword in ["experience", "employment", "work"]):
                continue
            
            # Get description from following elements
            description = []
            highlights = []
            
            for sibling in header.find_next_siblings():
                if sibling.name in ["h3", "h4", "h5"]:
                    break
                
                if sibling.name == "ul":
                    for li in sibling.find_all("li"):
                        highlights.append(li.get_text(strip=True))
                else:
                    description.append(sibling.get_text(strip=True))
            
            if title_text:
                exp = Experience(
                    title=title_text,
                    organization="",  # May need to be parsed from title
                    description=" ".join(description),
                    highlights=highlights
                )
                experience_items.append(exp)
        
        return experience_items
    
    def _parse_experience_entry(self, element: Any) -> Optional[Experience]:
        """Parse a single experience entry."""
        text = element.get_text(separator=" ", strip=True)
        
        # Try to find title
        title_elem = element.find(class_=re.compile(r"title|position|role"))
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Try to find organization
        org_elem = element.find(class_=re.compile(r"company|organization|employer|org"))
        organization = org_elem.get_text(strip=True) if org_elem else ""
        
        # Try to find dates
        date_elem = element.find(class_=re.compile(r"date|period|duration"))
        dates = date_elem.get_text(strip=True) if date_elem else ""
        
        # Parse date range
        start_date = ""
        end_date = ""
        if dates:
            date_match = re.search(r"(\w+\.?\s*\d{4})\s*[-–]\s*(\w+\.?\s*\d{4}|[Pp]resent|[Cc]urrent)", dates)
            if date_match:
                start_date = date_match.group(1)
                end_date = date_match.group(2)
        
        # Get highlights/bullet points
        highlights = []
        for li in element.find_all("li"):
            highlights.append(li.get_text(strip=True))
        
        # Get description
        desc_elem = element.find(class_=re.compile(r"description|summary|detail"))
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        if title or organization:
            return Experience(
                title=title,
                organization=organization,
                start_date=start_date,
                end_date=end_date,
                description=description,
                highlights=highlights
            )
        
        return None
    
    def _extract_research(self, soup: BeautifulSoup, profile: UserProfile) -> None:
        """Extract research interests."""
        research_selectors = [
            "#research", ".research", "#research-interests", ".research-interests",
            "section.research", "#interests", ".interests"
        ]
        
        research_interests = []
        
        for selector in research_selectors:
            element = soup.select_one(selector)
            if element:
                # Look for list items
                for li in element.find_all("li"):
                    interest = li.get_text(strip=True)
                    if interest:
                        research_interests.append(interest)
                
                # If no list, try to parse from text
                if not research_interests:
                    text = element.get_text(strip=True)
                    # Remove header text
                    for header in element.find_all(["h1", "h2", "h3", "h4"]):
                        text = text.replace(header.get_text(strip=True), "")
                    
                    # Split by common separators
                    interests = re.split(r'[,;|•]', text)
                    for interest in interests:
                        interest = interest.strip()
                        if interest and len(interest) > 3 and len(interest) < 200:
                            research_interests.append(interest)
                break
        
        # Also search by header
        if not research_interests:
            for header in soup.find_all(["h2", "h3", "h4"]):
                header_text = header.get_text(strip=True).lower()
                if "research" in header_text and "interest" in header_text:
                    for sibling in header.find_next_siblings():
                        if sibling.name in ["h2", "h3"]:
                            break
                        for li in sibling.find_all("li"):
                            interest = li.get_text(strip=True)
                            if interest:
                                research_interests.append(interest)
                    break
        
        profile.research_interests = research_interests
    
    def _extract_publications(self, soup: BeautifulSoup, profile: UserProfile) -> None:
        """Extract publications."""
        publications_selectors = [
            "#publications", ".publications", "#papers", ".papers",
            "section.publications", "#works", ".works"
        ]
        
        publications = []
        
        for selector in publications_selectors:
            element = soup.select_one(selector)
            if element:
                # Look for individual publication entries
                for entry in element.find_all(["li", "article", "div"], class_=re.compile(r"publication|paper|article")):
                    pub = self._parse_publication_entry(entry)
                    if pub:
                        publications.append(pub)
                
                # Also try simple list items
                if not publications:
                    for li in element.find_all("li"):
                        pub = self._parse_publication_entry(li)
                        if pub:
                            publications.append(pub)
                break
        
        profile.publications = publications
    
    def _parse_publication_entry(self, element: Any) -> Optional[Publication]:
        """Parse a single publication entry."""
        text = element.get_text(strip=True)
        
        if len(text) < 10:  # Too short to be a publication
            return None
        
        # Try to find title
        title_elem = element.find(class_=re.compile(r"title"))
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Try to find link
        link = element.find("a")
        url = link.get("href", "") if link else ""
        
        # If no explicit title, use link text or first part of text
        if not title:
            if link:
                title = link.get_text(strip=True)
            else:
                # Take first sentence or part before first period
                title = text.split(".")[0].strip()
        
        # Try to find year
        year = ""
        year_match = re.search(r"\(?(19|20)\d{2}\)?", text)
        if year_match:
            year = year_match.group(0).strip("()")
        
        # Try to find authors
        authors = ""
        # Common pattern: Authors (Year). Title. Venue.
        authors_match = re.match(r"^([^(]+)\s*\(\d{4}\)", text)
        if authors_match:
            authors = authors_match.group(1).strip()
        
        if title:
            return Publication(
                title=title,
                authors=authors,
                year=year,
                url=url
            )
        
        return None
    
    def _load_from_cache(self, source_path: str) -> Optional[UserProfile]:
        """Load profile from cache if valid."""
        if not self.cache_path.exists():
            return None
        
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check if cache is for the same source
            if data.get("source_path") != source_path:
                return None
            
            # Check if cache is still valid
            parsed_date = datetime.fromisoformat(data.get("parsed_date", "2000-01-01"))
            if datetime.now() - parsed_date > self.cache_duration:
                logger.debug("Cache expired")
                return None
            
            return UserProfile.from_dict(data)
        
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None
    
    def _save_to_cache(self, profile: UserProfile) -> None:
        """Save profile to cache."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, indent=2)
            logger.debug(f"Saved profile to cache: {self.cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def get_profile_for_matching(self) -> Dict[str, Any]:
        """
        Get profile data formatted for job matching.
        
        Returns a simplified dictionary optimized for the matching engine.
        """
        if not self.profile:
            raise ValueError("No profile loaded. Call parse() first.")
        
        return {
            "name": self.profile.name,
            "summary": self.profile.summary,
            "skills": self.profile.get_all_skills(),
            "education": self.profile.get_education_summary(),
            "experience": self.profile.get_experience_summary(),
            "research_interests": self.profile.research_interests,
            "years_of_experience": len(self.profile.experience),
            "highest_degree": self._get_highest_degree(),
        }
    
    def _get_highest_degree(self) -> str:
        """Determine highest degree from education."""
        degree_ranks = ["phd", "doctorate", "master", "msc", "ma", "mba", "mpa", "mpp", "bachelor", "bsc", "ba"]
        
        highest = ""
        highest_rank = len(degree_ranks)
        
        for edu in self.profile.education:
            degree_lower = edu.degree.lower()
            for i, rank in enumerate(degree_ranks):
                if rank in degree_lower:
                    if i < highest_rank:
                        highest_rank = i
                        highest = edu.degree
                    break
        
        return highest
    
    def get_profile_text(self) -> str:
        """
        Get full profile as formatted text for LLM context.
        
        This is useful for providing full context to Gemini for
        cover letter generation.
        """
        if not self.profile:
            raise ValueError("No profile loaded. Call parse() first.")
        
        sections = []
        
        if self.profile.name:
            sections.append(f"# {self.profile.name}")
        
        if self.profile.summary:
            sections.append(f"\n## Summary\n{self.profile.summary}")
        
        if self.profile.skills or self.profile.technical_skills:
            skills_text = "\n## Skills\n"
            if self.profile.technical_skills:
                skills_text += f"**Technical:** {', '.join(self.profile.technical_skills)}\n"
            if self.profile.skills:
                skills_text += f"**Other:** {', '.join(self.profile.skills)}\n"
            sections.append(skills_text)
        
        if self.profile.education:
            edu_text = "\n## Education\n"
            for edu in self.profile.education:
                edu_text += f"- {edu.degree}"
                if edu.field:
                    edu_text += f" in {edu.field}"
                edu_text += f", {edu.institution}"
                if edu.year:
                    edu_text += f" ({edu.year})"
                edu_text += "\n"
            sections.append(edu_text)
        
        if self.profile.experience:
            exp_text = "\n## Experience\n"
            for exp in self.profile.experience:
                exp_text += f"\n### {exp.title}"
                if exp.organization:
                    exp_text += f" at {exp.organization}"
                if exp.start_date:
                    exp_text += f"\n*{exp.start_date}"
                    if exp.end_date:
                        exp_text += f" - {exp.end_date}"
                    exp_text += "*"
                if exp.description:
                    exp_text += f"\n{exp.description}"
                if exp.highlights:
                    exp_text += "\n" + "\n".join(f"- {h}" for h in exp.highlights)
                exp_text += "\n"
            sections.append(exp_text)
        
        if self.profile.research_interests:
            sections.append(f"\n## Research Interests\n{', '.join(self.profile.research_interests)}")
        
        if self.profile.publications:
            pub_text = "\n## Publications\n"
            for pub in self.profile.publications:
                pub_text += f"- {pub.title}"
                if pub.year:
                    pub_text += f" ({pub.year})"
                pub_text += "\n"
            sections.append(pub_text)
        
        return "\n".join(sections)
