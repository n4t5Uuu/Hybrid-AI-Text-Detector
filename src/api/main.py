"""
HTTP API for the hybrid AI-text detector.

Run from the project root:
    uvicorn api.main:app --app-dir src --port 8000
Interactive docs: http://localhost:8000/docs
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from api.detector import MIN_PROSE_WORDS, THRESHOLD, Detector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(
    os.environ.get("HYBRID_MODEL_PATH", PROJECT_ROOT / "data" / "processed" / "models" / "xgb_hybrid.json")
)
MAX_INPUT_WORDS = 5000


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Hybrid model not found at {MODEL_PATH}; run model_development.ipynb first.")
    app.state.detector = Detector(MODEL_PATH)  # loads spaCy, ELECTRA and XGBoost once
    yield


app = FastAPI(title="Hybrid AI-Text Detector", lifespan=lifespan)


class DetectRequest(BaseModel):
    text: str = Field(..., description="The text to check.", max_length=60_000)


class PassageOut(BaseModel):
    text: str
    word_count: int
    ai_probability: float = Field(..., description="0-100")


class DetectResponse(BaseModel):
    ai_probability: float = Field(..., description="0-100, word-weighted over passages")
    label: Literal["AI-generated", "Human-written"]
    band: str
    threshold: float
    word_count: int
    passages: List[PassageOut]


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_PATH.name, "device": str(app.state.detector.device)}


@app.post("/detect", response_model=DetectResponse)
def detect(request: DetectRequest) -> DetectResponse:
    # Sync endpoint: FastAPI runs it in a worker thread, so scoring doesn't block the server.
    n_words = len(request.text.split())
    if n_words < MIN_PROSE_WORDS:
        raise HTTPException(422, f"Please paste at least {MIN_PROSE_WORDS} words (got {n_words}).")
    if n_words > MAX_INPUT_WORDS:
        raise HTTPException(422, f"Please paste at most {MAX_INPUT_WORDS} words (got {n_words}).")
    try:
        result = app.state.detector.predict(request.text)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    return DetectResponse(
        ai_probability=round(result.ai_probability * 100, 1),
        label="AI-generated" if result.is_ai else "Human-written",
        band=result.band,
        threshold=THRESHOLD,
        word_count=result.word_count,
        passages=[
            PassageOut(text=p.text, word_count=p.word_count, ai_probability=round(p.ai_probability * 100, 1))
            for p in result.passages
        ],
    )
