import os
import re
from typing import Any, Dict, List
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import asyncio
from functools import lru_cache
from app.schemas.course import CourseSchema
from datetime import datetime

load_dotenv()

# This module uses the YouTube Data API v3 to search for courses, so we need an API key.
# To get an API key, you need to create a project in the Google Developer Console and enable the YouTube Data API v3.
# More info: https://developers.google.com/youtube/registering_an_application
# Once you have the API key, you can create a `.env` file in the root of your project with the following content:
# API_KEY=your_youtube_api_key_here

API_KEY = os.getenv("API_KEY")
DEFAULT_NUM_ITEMS = 6

# Language search terms mapping
LANGUAGE_TERMS = {
    "es": "curso completo español",
    "en": "full course"
}


def convert_youtube_duration(iso_duration: str):
    """Convert YouTube's duration format to readable format"""
    if not iso_duration or not iso_duration.startswith('PT'):
        return None

    # Parse PT_H_M_S format
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, iso_duration)

    if not match:
        return None

    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return f"{seconds}s"


@lru_cache(maxsize=1)
def get_youtube_client():
    """
    Create and cache YouTube API client.
    Using LRU cache to avoid recreating the client on every request.
    """
    if not API_KEY:
        raise ValueError("YouTube API key not found in environment variables")

    return build("youtube", "v3", developerKey=API_KEY)


async def fetch_youtube_courses(
    query: str,
    lang: str = "en",
    num_items: int = DEFAULT_NUM_ITEMS
) -> Dict[str, Any]:
    """
    Fetch courses from YouTube API asynchronously.

    Args:
        query: Search term
        lang: Language code (es/en)
        num_items: Number of results to fetch

    Returns:
        Raw YouTube API response

    Raises:
        HttpError: If YouTube API request fails
        ValueError: If API key is missing
    """
    try:
        youtube = get_youtube_client()
        lang_string = LANGUAGE_TERMS.get(lang, LANGUAGE_TERMS["es"])

        # Run the blocking API call in a thread pool to keep it async
        def _search():
            return youtube.search().list(
                part="snippet",
                maxResults=min(num_items, 50),  # YouTube API limit is 50
                q=f"{query} {lang_string}",
                type="video",
                videoDuration="long",
                order="relevance"  # Get most relevant results first
            ).execute()

        # Execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _search)

        return response

    except HttpError as e:
        print(f"YouTube API error: {e}")
        return {"items": []}  # Return empty result instead of failing
    except Exception as e:
        print(f"Unexpected error fetching YouTube courses: {e}")
        return {"items": []}


async def fetch_detailed_video_info(video_ids: List[str]) -> Dict[str, Any]:
    """
    Fetch detailed video information for given video IDs.

    Args:
        video_ids: List of YouTube video IDs

    Returns:
        Raw YouTube API response with detailed video info

    Raises:
        HttpError: If YouTube API request fails
    """
    try:
        youtube = get_youtube_client()

        def _get_videos():
            return youtube.videos().list(
                part="snippet,contentDetails,player",
                id=",".join(video_ids)
            ).execute()

        # Execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _get_videos)

        return response

    except HttpError as e:
        print(f"YouTube API error: {e}")
        return {"items": []}
    except Exception as e:
        print(f"Unexpected error fetching detailed video info: {e}")
        return {"items": []}


def parse_youtube_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse and transform YouTube API response into standardized format.

    Args:
        data: Raw YouTube API response with video info

    Returns:
        List of parsed video dictionaries
    """
    items = data.get("items", [])
    videos = []

    for item in items:
        try:
            video_id = item.get("id")
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            # description = snippet.get("description", None)
            # player = item.get("player", {})

            # Skip if essential data is missing
            if not video_id or not snippet.get("title"):
                continue

            # Safely get thumbnail URL with fallback
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_high = (
                thumbnails.get("high", {}).get("url") or
                thumbnails.get("medium", {}).get("url") or
                thumbnails.get("default", {}).get("url")
            )

            duration = content_details.get("duration", None)
            if duration:
                duration = convert_youtube_duration(duration)

            publish_date_str = snippet.get('publishedAt', None)
            if publish_date_str:
                publish_date = datetime.fromisoformat(publish_date_str).date()
            
            video = CourseSchema(
                title=snippet.get("title").strip(),
                url=f"https://youtube.com/watch?v={video_id}",
                image_url=thumbnail_high,
                duration=duration,
                provider=snippet.get("channelTitle", None),
                provider_img=None,
                difficulty=None,
                avg_rating=None,
                count_rating=None,
                skills=None,
                course_date=publish_date
            )

            videos.append(video)

        except Exception as e:
            print(f"Error parsing detailed YouTube item: {e}")
            continue  # Skip malformed items instead of failing

    return videos


async def get_youtube_courses(
    query: str,
    lang: str = "en",
    num_items: int = DEFAULT_NUM_ITEMS
) -> List[Dict[str, Any]]:
    """
    Main function to search and parse YouTube courses.

    Args:
        query: Search term for courses
        lang: Language code (es for Spanish, en for English)
        num_items: Maximum number of courses to return

    Returns:
        List of course dictionaries with standardized format
    """
    if not query or not query.strip():
        return []

    # Sanitize inputs
    query = query.strip()
    lang = lang.lower() if lang else "en"
    num_items = max(1, min(num_items, 50))  # Ensure reasonable bounds

    try:
        # First, get basic search results
        raw_data = await fetch_youtube_courses(query, lang, num_items)

        # Extract video IDs from search results
        video_ids = []
        for item in raw_data.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id:
                video_ids.append(video_id)

        if not video_ids:
            return []

        # Get detailed information for these videos
        detailed_data = await fetch_detailed_video_info(video_ids)
        detailed_courses = parse_youtube_response(detailed_data)

        return detailed_courses

    except Exception as e:
        print(f"Error getting YouTube courses: {e}")
        return []  # Return empty list instead of failing
