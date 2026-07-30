import os

from dotenv import load_dotenv
from crewai import LLM

# ==========================================================
# Environment
# ==========================================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ==========================================================
# LLM
# ==========================================================

llm = LLM(
    model="gpt-4.1-mini",
    api_key=OPENAI_API_KEY,
    temperature=0.3
)

# ==========================================================
# Country Profiles
# ==========================================================

COUNTRY_PROFILE = {
    "Japan": {
        "language": "Japanese",
        "culture": "Japanese business interview culture",
        "style": "Polite, humble, team-oriented, respectful communication"
    },
    "USA": {
        "language": "English",
        "culture": "American interview culture",
        "style": "Confident, achievement-oriented, direct communication"
    },
    "Canada": {
        "language": "English",
        "culture": "Canadian workplace culture",
        "style": "Collaborative, respectful, inclusive communication"
    },
    "Australia": {
        "language": "English",
        "culture": "Australian workplace culture",
        "style": "Friendly, practical, honest communication"
    },
    "Singapore": {
        "language": "English",
        "culture": "Singaporean business culture",
        "style": "Professional, multicultural, concise communication"
    },
    "Korea": {
        "language": "Korean",
        "culture": "Korean business interview culture",
        "style": "Professional, logical, sincere, teamwork-oriented, respectful communication"
    }
}
