"""
Unit tests for the profile parser.
"""
import tempfile
import pytest
from pathlib import Path

# Note: These tests require the project dependencies to be installed
# Run with: pytest tests/test_profile_parser.py -v


# Sample HTML for testing
SAMPLE_PROFILE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>John Doe - Development Economist</title>
</head>
<body>
    <h1>John Doe</h1>
    <p>Development Economist | Researcher</p>
    
    <section id="about">
        <h2>About</h2>
        <p>Experienced development economist with expertise in impact evaluation,
        randomized controlled trials, and poverty reduction research.</p>
    </section>
    
    <section id="experience">
        <h2>Experience</h2>
        <div class="job">
            <h3>Research Associate</h3>
            <p>World Bank - 2020-2023</p>
            <p>Conducted impact evaluations of education programs in Sub-Saharan Africa.</p>
        </div>
        <div class="job">
            <h3>Research Assistant</h3>
            <p>MIT Abdul Latif Jameel Poverty Action Lab - 2018-2020</p>
            <p>Supported RCTs on financial inclusion in South Asia.</p>
        </div>
    </section>
    
    <section id="education">
        <h2>Education</h2>
        <p>Ph.D. in Economics - MIT, 2023</p>
        <p>M.A. in Economics - London School of Economics, 2018</p>
        <p>B.A. in Economics - University of California, Berkeley, 2016</p>
    </section>
    
    <section id="skills">
        <h2>Skills</h2>
        <ul>
            <li>Stata</li>
            <li>R</li>
            <li>Python</li>
            <li>Impact Evaluation</li>
            <li>Econometrics</li>
            <li>Survey Design</li>
        </ul>
    </section>
    
    <section id="publications">
        <h2>Publications</h2>
        <ul>
            <li>Doe, J. (2023). "The Effects of Cash Transfers on Education." Journal of Development Economics.</li>
            <li>Doe, J. & Smith, A. (2022). "Microfinance and Poverty." World Bank Economic Review.</li>
        </ul>
    </section>
</body>
</html>
"""


class TestProfileParser:
    """Test the profile parsing functionality."""
    
    @pytest.fixture
    def temp_html_file(self):
        """Create a temporary HTML file with sample profile."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(SAMPLE_PROFILE_HTML)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    def test_parse_local_profile(self, temp_html_file):
        """Test parsing a local HTML profile."""
        from src.profile.parser import ProfileParser
        
        parser = ProfileParser(local_path=temp_html_file)
        profile = parser.parse()
        
        assert profile is not None
        assert isinstance(profile, dict)
    
    def test_extract_skills(self, temp_html_file):
        """Test extracting skills from profile."""
        from src.profile.parser import ProfileParser
        
        parser = ProfileParser(local_path=temp_html_file)
        profile = parser.parse()
        
        skills = profile.get('skills', [])
        assert len(skills) > 0
        # Check for some expected skills
        skill_text = ' '.join(skills).lower()
        assert 'stata' in skill_text or 'python' in skill_text or 'r' in skill_text
    
    def test_extract_experience(self, temp_html_file):
        """Test extracting experience from profile."""
        from src.profile.parser import ProfileParser
        
        parser = ProfileParser(local_path=temp_html_file)
        profile = parser.parse()
        
        experience = profile.get('experience', [])
        assert len(experience) > 0
    
    def test_extract_education(self, temp_html_file):
        """Test extracting education from profile."""
        from src.profile.parser import ProfileParser
        
        parser = ProfileParser(local_path=temp_html_file)
        profile = parser.parse()
        
        education = profile.get('education', [])
        assert len(education) > 0
        # Check for expected degrees
        edu_text = ' '.join(str(e) for e in education).lower()
        assert 'phd' in edu_text or 'ph.d' in edu_text or 'economics' in edu_text
    
    def test_profile_caching(self, temp_html_file):
        """Test that profile parsing uses cache."""
        from src.profile.parser import ProfileParser
        
        parser = ProfileParser(local_path=temp_html_file)
        
        # Parse twice
        profile1 = parser.parse()
        profile2 = parser.parse()
        
        # Should return cached result
        assert profile1 == profile2
    
    def test_invalid_file_raises_error(self):
        """Test that invalid file path raises appropriate error."""
        from src.profile.parser import ProfileParser
        
        parser = ProfileParser(local_path="/nonexistent/path/profile.html")
        
        with pytest.raises(Exception):
            parser.parse()
    
    def test_get_profile_summary(self, temp_html_file):
        """Test getting profile summary text."""
        from src.profile.parser import ProfileParser
        
        parser = ProfileParser(local_path=temp_html_file)
        profile = parser.parse()
        summary = parser.get_profile_summary()
        
        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 100  # Should have substantial content


class TestProfileExtraction:
    """Test specific extraction patterns."""
    
    def test_extract_from_raw_html(self):
        """Test extraction from raw HTML string."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(SAMPLE_PROFILE_HTML, 'html.parser')
        
        # Test title extraction
        title = soup.find('title')
        assert title is not None
        assert 'John Doe' in title.get_text()
        
        # Test section extraction
        skills_section = soup.find('section', id='skills')
        assert skills_section is not None
        
        skill_items = skills_section.find_all('li')
        assert len(skill_items) == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
