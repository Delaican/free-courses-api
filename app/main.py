import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import resources

app = FastAPI(
    title="Free courses API",
    description="An API to explore free courses from different platform like Coursera, Udemy, and more.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(resources.router)

# TODO: Add documentation for each platform

# Endpoint base


@app.get("/")
def read_root():
    return {"message": "Welcome to the Free Courses API! 🚀"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
