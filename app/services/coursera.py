import uuid
from typing import Any, Dict, List, Optional
import httpx
from httpx import HTTPStatusError, RequestError

from app.schemas.course import CourseSchema


async def fetch_coursera_courses(
    query: str, lang: str = "English", num_items: int = 6
) -> Dict[str, Any]:
    """
    Makes HTTP request to Coursera API and returns raw response.

    Args:
        query: Search query string
        lang: Language filter (default: "English")
        num_items: Maximum number of items to return (default: 6)

    Returns:
        Raw JSON response from Coursera API

    Raises:
        HTTPStatusError: If API returns error status
        RequestError: If request fails
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")

    if num_items <= 0:
        raise ValueError("num_items must be positive")

    request_url = "https://www.coursera.org/graphql-gateway?opname=Search"

    # GraphQL query
    SEARCH_QUERY = """query Search($requests: [Search_Request!]!) {
        SearchResult {
            search(requests: $requests) {
                elements {
                    ... on Search_ProductHit {
                        name
                        url
                        imageUrl
                        productDifficultyLevel
                        productDuration
                        avgProductRating
                        numProductRatings
                        skills
                        partners
                        partnerLogos
                    }
                }
            }
        }
    }"""

    request_body = [
        {
            "operationName": "Search",
            "variables": {
                "requests": [
                    {
                        "entityType": "PRODUCTS",
                        "limit": num_items,
                        "facets": ["topic", "language"],
                        "sortBy": "BEST_MATCH",
                        "maxValuesPerFacet": 1000,
                        "facetFilters": [[f"language:{lang}", "price:Free"]],
                        "cursor": "0",
                        "query": query,
                    }
                ]
            },
            "query": SEARCH_QUERY,
        }
    ]

    headers = {
        "User-Agent": "PostmanRuntime/7.43.3",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "postman-token": str(uuid.uuid4()),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(request_url, headers=headers, json=request_body)
            response.raise_for_status()

            json_response = response.json()
            if not json_response or not isinstance(json_response, list):
                raise ValueError("Invalid response format from Coursera API")

            return json_response[0]

    except HTTPStatusError as e:
        raise HTTPStatusError(
            f"Coursera API returned error: {e.response.status_code}",
            request=e.request,
            response=e.response
        )
    except RequestError as e:
        raise RequestError(f"Failed to connect to Coursera API: {e}")


def parse_coursera_response(data: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """
    Extracts and transforms relevant elements from Coursera response.

    Args:
        data: Raw response data from Coursera API

    Returns:
        List of parsed course dictionaries with name, url, imageUrl, and difficulty
    """
    try:
        elements = (
            data.get("data", {})
            .get("SearchResult", {})
            .get("search", [{}])[0]
            .get("elements", [])
        )
    except (KeyError, IndexError, TypeError):
        # Return empty list if response structure is unexpected
        return []

    if not isinstance(elements, list):
        return []

    results = []
    for item in elements:
        if not isinstance(item, dict):
            continue

        # Build URL safely
        url_path = item.get("url")
        full_url = f"https://www.coursera.org{url_path}" if url_path else None

        # Normalize difficulty level
        difficulty = item.get("productDifficultyLevel", None)
        difficulty = difficulty.lower() if difficulty else None

        # Normalize duration
        duration = item.get("productDuration", None)
        if duration:
            duration = duration.lower()
            duration = duration.replace("_", " ")

        # round rating to 1 decimal place if it exists
        avg_rating = item.get('avgProductRating', None)
        if avg_rating is not None:
            avg_rating = round(avg_rating, 1)

        course = CourseSchema(
            title=item.get('name'),
            url=full_url,
            image_url=item.get('imageUrl'),
            duration=duration,
            provider=item.get('partners', [None])[0],
            provider_img=item.get('partnerLogos', [None])[0],
            difficulty=difficulty,
            avg_rating=avg_rating,
            count_rating=item.get('numProductRatings'),
            skills=item.get('skills', None)
        )

        results.append(course)

    return results


async def get_coursera_courses(
    query: str, lang: str = "English", num_items: int = 6
) -> List[Dict[str, Optional[str]]]:
    """
    Main function that combines request and processing for use from routers.

    Args:
        query: Search query string
        lang: Language filter (default: "English")
        num_items: Maximum number of items to return (default: 6)

    Returns:
        List of parsed course dictionaries

    Raises:
        ValueError: If input parameters are invalid
        HTTPStatusError: If API returns error status
        RequestError: If request fails
    """
    raw_data = await fetch_coursera_courses(query, lang, num_items)
    courses = parse_coursera_response(raw_data)
    return courses
