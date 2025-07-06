from pydantic import BaseModel, HttpUrl
from typing import Optional, List


class CourseSchema(BaseModel):
    """Normalized course schema for all platforms"""

    # Core fields
    title: str
    url: HttpUrl
    image_url: Optional[HttpUrl]

    # Optional fields
    duration: Optional[str] = None
    provider: Optional[str] = None
    provider_img: Optional[HttpUrl] = None
    difficulty: Optional[str] = None
    avg_rating: Optional[float] = None
    count_rating: Optional[int] = None
    skills: Optional[List[str]] = None

    class Config:
        # Example for documentation
        json_schema_extra = {
            "example": {
                "title": "Python for Data Science",
                "url": "https://coursera.org/learn/python-data-science",
                "image_url": "https://example.com/image.jpg",
                "duration": "4 weeks",
                "provider": "John Doe",
                "provider_img": "https://example.com/provider-logo.jpg",
                "difficulty": "beginner",
                "avg_rating": 4.5,
                "count_rating": 1500,
                "skills": ["Python", "Data Analysis", "Pandas"]
            }
        }


class PlatformResponse(BaseModel):
    """Response schema for each platform"""
    courses: List[CourseSchema]
    redirect_url: Optional[str] = None
    total_found: Optional[int] = None


class ApiResponse(BaseModel):
    """Main API response schema"""
    results: dict[str, PlatformResponse]
    query: Optional[str] = None
    total_courses: Optional[int] = None
