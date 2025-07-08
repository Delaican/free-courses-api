from urllib.parse import quote
from enum import Enum
from typing import Dict, Any
from fastapi import APIRouter, Query, HTTPException

from app.services.coursera import get_coursera_courses
from app.services.edx import get_edx_courses
from app.services.udemy import get_udemy_courses
from app.services.youtube import get_youtube_courses


class Language(str, Enum):
    """Supported languages for course search."""
    SPANISH = "es"
    ENGLISH = "en"


router = APIRouter(prefix="/resources", tags=["courses"])

# TODO: Establish display order for platforms based on type of course
# and language, e.g., prioritize YouTube for Spanish courses, etc.

# TODO: If a platform returns empty in spanish, suggest results
# with ai translate or subtitles

@router.get("/courses")
async def search_courses(
    q: str = Query(..., description="Search term for courses", min_length=1, example="python"),
    lang: Language = Query(Language.ENGLISH, description="Search language (es: Spanish, en: English)"),
    num_items: int = Query(6, description="Number of items to return per platform"),
) -> Dict[str, Any]:
    """
    Search for free courses across multiple platforms.

    Returns courses from YouTube, Udemy, Coursera and edX with redirect URLs.
    """
    # Validate input
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    query = q.strip()
    encoded_query = quote(query)

    # Language mappings for each platform
    lang_codes = {
        "coursera": "Spanish" if lang == Language.SPANISH else "English",
        "edx": "Spanish" if lang == Language.SPANISH else "English",
        "udemy": lang.value.upper(),
        "youtube": "curso+completo+español" if lang == Language.SPANISH else "full+course",
    }

    # Search all platforms concurrently
    try:
        coursera_courses = await get_coursera_courses(query, lang=lang_codes["coursera"], num_items=num_items)
    except Exception as e:
        print(f"Coursera search failed: {e}")
        coursera_courses = []

    try:
        edx_courses = await get_edx_courses(query, lang=lang_codes["edx"], num_items=num_items)
    except Exception as e:
        print(f"edX search failed: {e}")
        edx_courses = []

    try:
        udemy_courses = await get_udemy_courses(query, lang=lang_codes["udemy"], num_items=num_items)
    except Exception as e:
        print(f"Udemy search failed: {e}")
        udemy_courses = []

    try:
        youtube_courses = await get_youtube_courses(query, lang.value, num_items=num_items)
    except Exception as e:
        print(f"YouTube search failed: {e}")
        youtube_courses = []

    # Build redirect URLs for each platform
    coursera_url = f"https://coursera.org/search?query={encoded_query}&language={lang_codes['coursera']}"
    edx_url = f"https://www.edx.org/search?q={encoded_query}&language={lang_codes['edx']}&availability=Available+now"
    udemy_url = f"https://www.udemy.com/courses/search/?lang={lang_codes['udemy']}&price=price-free&q={encoded_query}"
    youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}+{lang_codes['youtube']}"

    # Combine results
    results = {
        "results": {
            "coursera": {
                "courses": coursera_courses,
                "redirect_url": coursera_url,
            },
            "edx": {
                "courses": edx_courses,
                "redirect_url": edx_url,
            },
            "udemy": {
                "courses": udemy_courses,
                "redirect_url": udemy_url,
            },
            "youtube": {
                "courses": youtube_courses,
                "redirect_url": youtube_url,
            }
        }
    }

    return results
