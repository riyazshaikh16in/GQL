# gemini_quiz_backend.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict
import os
import uuid
import json
import uvicorn

# Google GenAI SDK
from google import genai  # pip install google-genai

# ---------------- Config ----------------
# Prefer environment variable in production:
#   GEMINI_API_KEY set in your hosting provider
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyD_HJNKA3QwjBP7nf8ssdYYFAO8qPtOQKg")
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

app = FastAPI(title="Gemini Quiz API")

# Allow Streamlit local; add your deployed frontend origin here when live
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        # "https://your-streamlit-app.onrender.com",  # add when deployed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NextReq(BaseModel):
    category: str = Field(..., description="science, history, geography, sports, biology, general knowledge")
    difficulty: str = Field("progressive", description="easy|medium|hard|progressive")

class QuizItem(BaseModel):
    id: str
    category: str
    difficulty: str
    question: str
    options: Dict[str, str]  # A,B,C,D
    answer: str              # A|B|C|D
    explanation: str

def build_prompt(category: str, difficulty: str) -> str:
    return f"""
You are a quiz generator. Create exactly ONE high‑quality multiple-choice question in English.

Topic category: {category}
Target difficulty: {difficulty}

Output STRICTLY a compact JSON object with these keys and nothing else:
{{
  "question": "...",
  "options": {{"A":"...", "B":"...", "C":"...", "D":"..."}},
  "answer": "A|B|C|D",
  "explanation": "short reason (1 sentence)"
}}

Rules:
- Make options concise and mutually exclusive.
- Ensure only one correct answer.
- Do not use markdown, backticks, or extra commentary.
- Keep explanation short and factual.
""".strip()

def get_client() -> genai.Client:
    try:
        return genai.Client()  # reads GEMINI_API_KEY from env
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini client init failed: {e}")

# Root for generic health probes
@app.get("/")
def root():
    return {"ok": True, "service": "Gemini Quiz API"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/quiz/next", response_model=QuizItem)
def next_question(req: NextReq):
    client = get_client()
    prompt = build_prompt(req.category.strip(), req.difficulty.strip())
    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        text = (resp.text or "").strip()

        # Strip code fences if the model wrapped JSON
        if text.startswith("```"):
            text = text[3:]
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        data = json.loads(text)

        q = data.get("question")
        options = data.get("options") or {}
        ans = data.get("answer")
        exp = data.get("explanation") or ""

        if not (q and isinstance(options, dict) and set(options.keys()) == {"A","B","C","D"} and ans in {"A","B","C","D"}):
            raise ValueError("Model returned invalid schema")

        return QuizItem(
            id=str(uuid.uuid4()),
            category=req.category,
            difficulty=req.difficulty,
            question=q,
            options=options,
            answer=ans,
            explanation=exp,
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Model returned non-JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

if __name__ == "__main__":
    # Bind to 0.0.0.0 and $PORT for PaaS; default to 8000 locally
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("gemini_quiz_backend:app", host="0.0.0.0", port=port)
