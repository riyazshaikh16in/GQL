# gemini_quiz_backend.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Tuple
import os
import uuid
import json
import uvicorn
import random
from collections import defaultdict, deque

# Google GenAI SDK
from google import genai  # pip install google-genai

# ---------------- Config ----------------
# Prefer environment variable in production:
#   GEMINI_API_KEY set in your hosting provider
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyD_HJNKA3QwjBP7nf8ssdYYFAO8qPtOQKg")
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

app = FastAPI(title="Gemini Quiz API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        # "https://your-streamlit-app.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Recent question memory (to avoid repeats) ----------------
MAX_RECENT = 50
_recent_deques = defaultdict(lambda: deque(maxlen=MAX_RECENT))  # key -> deque of str
_recent_sets = defaultdict(set)  # key -> set for quick lookup

def _key(cat: str, diff: str) -> Tuple[str, str]:
    return (cat.lower().strip(), diff.lower().strip())

def mark_seen(cat: str, diff: str, q: str):
    key = _key(cat, diff)
    if q in _recent_sets[key]:
        return
    _recent_deques[key].append(q)
    _recent_sets[key].add(q)
    # If deque evicted, rebuild set (rare)
    if len(_recent_sets[key]) > len(_recent_deques[key]):
        _recent_sets[key] = set(_recent_deques[key])

def is_seen(cat: str, diff: str, q: str) -> bool:
    return q in _recent_sets[_key(cat, diff)]

# ---------------- Models & I/O ----------------
class NextReq(BaseModel):
    category: str = Field(..., description="mathematics, science, history, geography, sports, biology, general knowledge")
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
        return genai.Client()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini client init failed: {e}")

@app.get("/")
def root():
    return {"ok": True, "service": "Gemini Quiz API"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ---------------- Core helpers ----------------
def generate_unique_question(client: genai.Client, category: str, difficulty: str, attempts: int = 4):
    last_err = None
    for _ in range(attempts):
        try:
            prompt = build_prompt(category, difficulty)
            resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = (resp.text or "").strip()

            # Strip code fences if present
            if text.startswith("```"):
                text = text[3:]
                if text.lstrip().lower().startswith("json"):
                    text = text.lstrip()[4:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            data = json.loads(text)

            q = (data.get("question") or "").strip()
            options = data.get("options") or {}
            ans = data.get("answer")
            exp = data.get("explanation") or ""

            if not (q and isinstance(options, dict) and set(options.keys()) == {"A","B","C","D"} and ans in {"A","B","C","D"}):
                raise ValueError("Model returned invalid schema")

            # reject duplicates
            if is_seen(category, difficulty, q):
                last_err = ValueError("Duplicate question")
                continue

            return q, options, ans, exp
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=502, detail=f"Unable to get a unique question: {last_err}")

def shuffle_options(options: Dict[str, str], correct_label: str):
    # keep correct text, shuffle values, reassign to A-D
    correct_text = options[correct_label]
    values = list(options.values())
    random.shuffle(values)
    labels = ["A", "B", "C", "D"]
    shuffled = {lbl: val for lbl, val in zip(labels, values)}
    new_correct = next(lbl for lbl, val in shuffled.items() if val == correct_text)
    return shuffled, new_correct

# ---------------- Endpoint ----------------
@app.post("/quiz/next", response_model=QuizItem)
def next_question(req: NextReq):
    client = get_client()
    category = req.category.strip()
    difficulty = req.difficulty.strip()

    q, options, ans, exp = generate_unique_question(client, category, difficulty)
    options_shuffled, new_ans = shuffle_options(options, ans)
    mark_seen(category, difficulty, q)

    return QuizItem(
        id=str(uuid.uuid4()),
        category=category,
        difficulty=difficulty,
        question=q,
        options=options_shuffled,
        answer=new_ans,
        explanation=exp,
    )

if __name__ == "__main__":
    # Bind to 0.0.0.0 and $PORT for PaaS; default to 8000 locally
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("GQL_back:app", host="0.0.0.0", port=port)
