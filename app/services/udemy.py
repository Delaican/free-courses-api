from typing import Any, Dict, List, Optional
import json
import requests
from httpx import HTTPStatusError, RequestError
from app.schemas.course import CourseSchema
from datetime import datetime

async def fetch_udemy_courses(
    query: str, lang: str = "EN", num_items: int = 6
) -> Dict[str, Any]:
    """
    Makes HTTP request to Udemy API and returns raw response.

    Args:
        query: Search query string
        lang: Language filter (default: "EN")
        num_items: Maximum number of items to return (default: 6)
    Returns:
        Raw JSON response from Udemy API

    Raises:
        HTTPStatusError: If API returns error status
        RequestError: If request fails
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")

    if num_items <= 0:
        raise ValueError("num_items must be positive")

    request_url = "https://www.udemy.com/api/2024-01/graphql/"

    # GraphQL query
    SEARCH_QUERY = """
    query SrpMxCourseSearch($query: String!, $page: NonNegativeInt!, $pageSize: MaxResultsPerPage!, $sortOrder: CourseSearchSortType, $filters: CourseSearchFilters, $context: CourseSearchContext) {
      courseSearch(
        query: $query
        page: $page
        pageSize: $pageSize
        sortOrder: $sortOrder
        filters: $filters
        context: $context
      ) {
        count
        results {
          course {
            durationInSeconds
            headline
            id
            images { height125 px100x100 px240x135 px304x171 px480x270 px50x50 }
            instructors { id name }
            isFree
            learningOutcomes
            level
            updatedOn
            locale
            rating { average count }
            title
            urlCourseLanding
          }
        }
        page
        pageCount
        metadata {
          querySuggestion { query type }
          originalQuery
          associatedTopic { id url }
        }
      }
    }
    """

    payload = json.dumps({
        "query": SEARCH_QUERY,
        "variables": {
            "page": 0,
            "query": query,
            "sortOrder": "RELEVANCE",
            "pageSize": num_items,
            "context": {
                "triggerType": "USER_QUERY"
            },
            "filters": {
                "price": [
                    "FREE"
                ],
                "language": [
                    lang
                ]
            }
        },
    })

    headers = {
        "Content-Type": "application/json",
    }

    # Do the request and handle errors
    try:
        # TODO: Find a way to make httpx work here
        response = requests.post(
            request_url, headers=headers, data=payload, timeout=30.0
        )
        response.raise_for_status()

        json_response = response.json()
        if not json_response or not isinstance(json_response, dict):
            raise ValueError("Invalid response format from Udemy API")

        return json_response

    except HTTPStatusError as e:
        raise HTTPStatusError(
            f"Udemy API returned error: {e.response.status_code}",
            request=e.request,
            response=e.response,
        )
    except RequestError as e:
        raise RequestError(f"Failed to connect to Udemy API: {e}")


def parse_udemy_response(data: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """
    Extracts and transforms relevant elements from Udemy response.

    Args:
        data: Raw response data from Udemy API

    Returns:
        List of parsed course dictionaries with name, url, imageUrl, and difficulty
    """
    try:
        elements = data.get("data", {}).get("courseSearch", {}).get("results", [])
    except (KeyError, IndexError, TypeError):
        # Return empty list if response structure is unexpected
        return []

    if not isinstance(elements, list):
        return []

    results = []
    for item in elements:
        if not isinstance(item, dict):
            continue

        course_data = item.get("course", {})

        duration = course_data.get("durationInSeconds", None)
        if duration:
            hours, remainder = divmod(duration, 3600)
            duration = f"{hours}h {remainder // 60}m"

        provider = course_data.get("instructors", None)
        if provider:
            provider = provider[0].get("name")

        difficulty = course_data.get("level", None)
        if difficulty:
            difficulty = difficulty.lower().replace("_", " ")

        rating = course_data.get("rating", None)
        if rating:
            avg_rating = round(rating.get("average"), 1)
            count_rating = rating.get("count")

        course_date = course_data.get("updatedOn", None)
        if course_date:
            # Convert to date object
            course_date = datetime.strptime(course_date, "%Y-%m-%d").date()

        course = CourseSchema(
            title=course_data.get("title").strip(),
            url=course_data.get("urlCourseLanding"),
            image_url=course_data.get("images").get("px240x135"),
            duration=duration,
            provider=provider,
            provider_img=None,
            difficulty=difficulty,
            avg_rating=avg_rating,
            count_rating=count_rating,
            skills=course_data.get("learningOutcomes", None),
            course_date=course_date
        )

        results.append(course)

    return results


async def get_udemy_courses(
    query: str, lang: str = "EN", num_items: int = 6
) -> List[Dict[str, Optional[str]]]:
    """
    Main function that combines request and processing for use from routers.

    Args:
        query: Search query string
        lang: Language filter (default: "EN")
        num_items: Maximum number of items to return (default: 6)

    Returns:
        List of parsed course dictionaries

    Raises:
        ValueError: If input parameters are invalid
        HTTPStatusError: If API returns error status
        RequestError: If request fails
    """
    raw_data = await fetch_udemy_courses(query, lang, num_items)
    courses = parse_udemy_response(raw_data)
    return courses
