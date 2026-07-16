"""
tests/conftest.py — pytest session setup.

Loads environment variables from .env before any test module is imported,
so that GROQ_API_KEY and other settings are available when src.classify and
src.retrieve read their os.getenv() calls at module import time.
"""
import time
from pathlib import Path
from dotenv import load_dotenv
import pytest

# Load .env from the project root (one directory above tests/)
load_dotenv(Path(__file__).parent.parent / ".env")


# ---------------------------------------------------------------------------
# Inter-fixture pacing — Groq free tier allows 30 RPM.
# Each scenario makes 2 Groq calls (retrieve + classify), so 5 scenarios = 10
# calls total.  A 3-second pause between module-scoped fixtures keeps us well
# inside the rate limit.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="module")
def _rate_limit_pause():
    """Pause briefly before each module-scoped fixture to avoid 429s."""
    time.sleep(3)
    yield
