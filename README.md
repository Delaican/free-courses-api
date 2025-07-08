# Free Courses API

A FastAPI that finds free courses from Coursera, edX, Udemy and YouTube in one search.

## Features

- **Multi-platform search**: Get courses from 4 major platforms at once
- **Fast performance**: Direct API calls (no web scraping)
- **Unified format**: All courses returned in consistent JSON structure
- **Multi-language**: Search in Spanish and English

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Delaican/free-courses-api.git

cd free-courses-api

# Create and activate virtual environment
python3 -m venv .venv

source .venv/bin/activate

# Install
pip install -r requirements.txt

# Setup environment
echo "API_KEY = youtube_API_key" >> .env
# Add your youtube API key to .env
# To get an API key, you need to create a project in the Google Developer Console and enable the YouTube Data API v3.
# More info: https://developers.google.com/youtube/registering_an_application

# Run
python3 -m app.main
```

## API Call Example

```
http://127.0.0.1:8000/resources/courses?q=spanish

http://127.0.0.1:8000/resources/courses?q=python&lang=es&num_items=3
```

## API Response

```json
{
    "results": {
        "coursera": {
            "courses": [
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
            ],
            "redirect_url": coursera_url,
        },
        "edx": {
            ...
        },
        "udemy": {
            ...
        },
        "youtube": {
            ...
        }
    }
}
```

## Why This Approach?

- **10x faster** than web scraping
- **More reliable** - no browser dependencies
- **Better data quality** - structured API responses
- **Easier maintenance** - APIs are more stable than web pages

## Use Cases

- Course discovery platforms
- Learning management systems
- Educational dashboards
- Research on online education trends

Built with FastAPI for speed and reliability.
