import os
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import AnalyzeRequest, AnalyzeResponse, PreprocessRequest, PreprocessResponse
from .gemini_preprocess import preprocess_code
from .ast_analyzer import analyze_python_code


logger = logging.getLogger("codeflowviz")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Code Flow Viz", version="0.1.0")

# CORS for local dev and general usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/preprocess", response_model=PreprocessResponse)
def api_preprocess(req: PreprocessRequest):
    try:
        cleaned_code, meta = preprocess_code(req.code or "", prefer_gemini=req.use_gemini)
        return PreprocessResponse(clean_code=cleaned_code, meta=meta)
    except Exception as exc:
        logger.exception("Preprocess failed")
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/analyze", response_model=AnalyzeResponse)
def api_analyze(req: AnalyzeRequest):
    try:
        cleaned_code, meta = preprocess_code(req.code or "", prefer_gemini=req.use_gemini)
        graph, diagnostics, stats = analyze_python_code(cleaned_code)
        return AnalyzeResponse(clean_code=cleaned_code, graph=graph, diagnostics=diagnostics, meta=meta, stats=stats)
    except Exception as exc:
        logger.exception("Analyze failed")
        raise HTTPException(status_code=400, detail=str(exc))


# Sample route for convenience
@app.get("/api/sample")
def api_sample():
    sample = """
import math

def area_of_circle(r):
    pi = 3.14159
    a = pi * r ** 2
    return a

x = 5
result = area_of_circle(x)
print(result)
""".strip()
    return {"code": sample}


# Serve frontend last so API routes take precedence
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)