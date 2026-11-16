from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.schemas import RoastRequest, RoastResponse
from app.prompts import build_prompt
from app.safety import validate_input
from app.providers import generate, ProviderError

app = FastAPI(title="COOKED API", description="Writes short, playful comments about harmless situations.", version="1.0.0")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    return (STATIC / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "COOKED"}

@app.post("/api/roast", response_model=RoastResponse)
async def roast(payload: RoastRequest):
    try:
        validate_input(payload.text)
        prompt = build_prompt(payload.text, payload.style, payload.intensity)
        answer = await generate(
            prompt,
            payload.text,
            style=payload.style,
        )
        return RoastResponse(roast=answer, style=payload.style)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
