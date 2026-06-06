"""
ATC Learning Platform — FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import content, flashcards, lessons, quizzes, review

app = FastAPI(
    title="ATC 7110.65 Learning Platform",
    description="Study platform for FAA Order JO 7110.65 — Air Traffic Control",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(content.router, prefix="/api/content", tags=["Content"])
app.include_router(flashcards.router, prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(quizzes.router, prefix="/api/quizzes", tags=["Quizzes"])
app.include_router(lessons.router, prefix="/api/lessons", tags=["Lessons"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])


@app.get("/health")
def health():
    return {"status": "ok"}
