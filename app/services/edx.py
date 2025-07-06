import uuid
from typing import Any, Dict, List, Optional
import httpx
from httpx import TimeoutException, RequestError, HTTPStatusError
import asyncio
from app.schemas.course import CourseSchema

# Constants
DEFAULT_TIMEOUT = 15.0
MAX_RETRIES = 2
DEFAULT_NUM_ITEMS = 6
MAX_ITEMS_LIMIT = 50

# Language mapping for edX API
LANGUAGE_MAP = {
    "es": "Spanish",
    "en": "English",
}

# edX API configuration
EDX_API_CONFIG = {
    "base_url": "https://igsyv1z1xi-dsn.algolia.net/1/indexes/*/queries",
    "app_id": "IGSYV1Z1XI",
    "api_key": "6658746ce52e30dacfdd8ba5f8e8cf18",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class EdxAPIError(Exception):
    """Custom exception for edX API errors."""
    pass


def build_edx_request_body(query: str, language: str, num_items: int) -> Dict[str, Any]:
    """
    Build the request body for edX API.

    Args:
        query: Search term
        language: Language filter
        num_items: Number of results to fetch

    Returns:
        Request body dictionary
    """
    return {
        "requests": [
            {
                "indexName": "product",
                "clickAnalytics": False,
                "facetFilters": [
                    ["availability:Available now"],
                    [f"language:{language}"]
                ],
                "facets": [
                    "availability",
                    "language",
                    "learning_type",
                    "level",
                    "product",
                    "program_type",
                    "skills.skill",
                    "subject",
                ],
                "filters": (
                    '(product:"Course" OR product:"Program" OR product:"Executive Education" OR product:"2U Degree") '
                    'AND (blocked_in:null OR NOT blocked_in:"CO") '
                    'AND (allowed_in:null OR allowed_in:"CO")'
                ),
                "hitsPerPage": min(num_items, MAX_ITEMS_LIMIT),
                "maxValuesPerFacet": 100,
                "query": query.strip(),
                "page": 0
            }
        ]
    }


async def fetch_edx_courses(
    query: str,
    lang: str = "English",
    num_items: int = DEFAULT_NUM_ITEMS
) -> Optional[Dict[str, Any]]:
    """
    Fetch courses from edX API with proper error handling and retries.

    Args:
        query: Search term
        lang: Language for search results
        num_items: Number of results to fetch

    Returns:
        Raw edX API response or None if request fails
    """
    if not query.strip():
        return None

    # Build request URL with parameters
    url_params = (
        f"?x-algolia-agent=Algolia%20for%20JavaScript%20(5.0.0)%3B%20Search%20(5.0.0)"
        f"&x-algolia-api-key={EDX_API_CONFIG['api_key']}"
        f"&x-algolia-application-id={EDX_API_CONFIG['app_id']}"
    )
    request_url = EDX_API_CONFIG["base_url"] + url_params

    # Build request body
    request_body = build_edx_request_body(query.strip(), lang, num_items)

    # Request headers
    headers = {
        "User-Agent": EDX_API_CONFIG["user_agent"],
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "postman-token": str(uuid.uuid4()),
        "Referer": "https://www.edx.org/",
        "Origin": "https://www.edx.org"
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(request_url, headers=headers, json=request_body)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    print(f"edX API rate limited (attempt {attempt + 1})")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None
                else:
                    print(f"edX API request failed: {response.status_code}")
                    return None

        except TimeoutException:
            print(f"Timeout on edX request (attempt {attempt + 1})")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(1)
                continue
            return None

        except HTTPStatusError as e:
            print(f"HTTP error from edX API: {e.response.status_code}")
            return None

        except RequestError as e:
            print(f"Network error on edX request: {e}")
            return None

        except Exception as e:
            print(f"Unexpected error in edX request: {e}")
            return None

    return None


def parse_edx_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse and transform edX API response into standardized format.

    Args:
        data: Raw edX API response

    Returns:
        List of parsed course dictionaries
    """
    if not data:
        return []

    try:
        # Navigate to the hits array safely
        results = data.get("results", [])
        if not results:
            return []

        hits = results[0].get("hits", [])
        if not hits:
            return []

        courses = []

        for item in hits:
            try:
                # Extract provider data
                owner = item.get("owners", [])
                if owner:
                    provider = owner[0].get("name", None)
                    provider_img = owner[0].get("logoImageUrl", None)
                else:
                    provider = None

                duration = item.get('weeks_to_complete', None)
                if duration:
                    duration = f"{duration} weeks"

                skills = item.get("skills", None)
                if skills:
                    skills = [item.get('skill') for item in skills]

                # Build course object
                course = CourseSchema(
                    title=item.get("title").strip(),
                    url=item.get("marketing_url"),
                    image_url=item.get("card_image_url", None),
                    duration=duration,
                    provider=provider,
                    provider_img=provider_img,
                    difficulty=item.get("level", [None])[0],
                    avg_rating=None,
                    count_rating=None,
                    skills=skills,
                )

                courses.append(course)

            except Exception as e:
                print(f"Error parsing edX course item: {e}")
                continue  # Skip malformed items

        return courses

    except Exception as e:
        print(f"Error parsing edX response: {e}")
        return []


async def get_edx_courses(
    query: str,
    lang: str = "English",
    num_items: int = DEFAULT_NUM_ITEMS
) -> List[Dict[str, Any]]:
    """
    Main function to search and retrieve edX courses.

    Args:
        query: Search term for courses
        lang: Language for search results (Spanish, English, etc.)
        num_items: Maximum number of courses to return

    Returns:
        List of course dictionaries with standardized format
    """
    if not query or not query.strip():
        return []

    # Validate and sanitize inputs
    query = query.strip()
    num_items = max(1, min(num_items, MAX_ITEMS_LIMIT))

    # Map language code to full name if needed
    if len(lang) == 2:  # If it's a language code like 'es', 'en'
        lang = LANGUAGE_MAP.get(lang.lower(), "English")

    try:
        # Fetch raw data from edX API
        raw_data = await fetch_edx_courses(query, lang, num_items)
        if not raw_data:
            print(f"No data returned from edX API for query: {query}")
            return []

        # Parse and return courses
        courses = parse_edx_response(raw_data)
        return courses

    except Exception as e:
        print(f"Error getting edX courses: {e}")
        return []
