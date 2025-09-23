# gully_quiz_league_frontend.py
import streamlit as st
import requests

# BACKEND = "http://127.0.0.1:9321/quiz/next"

BACKEND = "https://gql-backend.onrender.com/quiz/next"

# ------------------- Page config & theme -------------------
st.set_page_config(page_title="Gully Quiz League", page_icon="💎", layout="wide")

st.markdown("""
# <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&family=Orbitron:wght@700;800&display=swap" rel="stylesheet">
<style>
.stApp {
  background: radial-gradient(1400px 700px at 50% -10%, #0f1432 0%, #0b1121 50%, #080e1c 100%);
  color: #e6edff;
  font-family: 'Poppins', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Helvetica Neue", Arial;
}
.kbc-title {
  text-align:center; font-family:'Orbitron',sans-serif; font-weight:800; letter-spacing:.08em;
  font-size:42px; margin:.4rem 0 1rem 0;
  background: linear-gradient(90deg, #d4b106 0%, #f6ff00 40%, #00e5ff 60%, #6c5ce7 100%);
  -webkit-background-clip:text; background-clip:text; color:transparent; text-shadow:0 6px 18px rgba(0,0,0,.55);
}
.card {
  border-radius: 20px; padding: 1.0rem 1.4rem;
  background: linear-gradient(180deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.035) 100%);
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 24px 48px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.08);
}
.q-text { font-size:22px; line-height:1.55; font-weight:700; color:#cbd5ff; } /* darker for visibility */

.answer-tile {
  width:100%; border-radius:14px; padding:14px 16px; text-align:left; font-size:18px; line-height:1.35;
  border:1px solid rgba(255,255,255,0.14);
  background: linear-gradient(180deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.05) 100%);
  color:#e8f0ff; box-shadow:0 16px 30px rgba(0,0,0,0.42), inset 0 1px 0 rgba(255,255,255,0.06);
}
.answer-correct { background: linear-gradient(180deg,#0f6b3e 0%,#0b4a2c 100%) !important; border-color:#22c55e !important; color:#eafff5 !important; }
.answer-wrong   { background: linear-gradient(180deg,#6b232c 0%,#46171d 100%) !important; border-color:#ef4444 !important; color:#ffecef !important; }
.answer-dim     { opacity:.55; }

.small-btn {
  padding:.35rem .7rem; font-size:.9rem; border-radius:999px; border:1px solid rgba(255,255,255,.18);
  background:linear-gradient(135deg,#5eead4 0%, #60a5fa 100%); color:#0b1220; font-weight:800;
  box-shadow:0 10px 20px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.45);
}

.pill {
  display:inline-block; padding:.28rem .7rem; border-radius:999px; font-weight:800;
  margin-right:.5rem; font-size:.9rem; border:1px solid rgba(255,255,255,.18);
}
.pill-green { background:linear-gradient(135deg,#22c55e 0%, #16a34a 100%); color:#06130b; }
.pill-red   { background:linear-gradient(135deg,#ef4444 0%, #b91c1c 100%); color:#1d0406; }
</style>
""", unsafe_allow_html=True)

# ------------------- Session State -------------------
defaults = {
    "question": None,
    "selected": None,
    "correct": None,
    "explanation": "",
    "category": "general knowledge",
    "difficulty": "progressive",
    "score_right": 0,
    "score_wrong": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ------------------- Helpers -------------------
def fetch_next_question():
    r = requests.post(
        BACKEND,
        json={"category": st.session_state.category, "difficulty": st.session_state.difficulty},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    st.session_state.question = {"text": data["question"], "options": data["options"]}
    st.session_state.correct = data["answer"]
    st.session_state.explanation = data.get("explanation", "")
    st.session_state.selected = None

def finalize_outcome(selected_label: str):
    if selected_label == st.session_state.correct:
        st.session_state.score_right += 1
    else:
        st.session_state.score_wrong += 1

def reset_game():
    st.session_state.score_right = 0
    st.session_state.score_wrong = 0
    st.session_state.selected = None
    st.session_state.question = None      # <- keeps label as "Start ▶"
    st.session_state.correct = None
    st.session_state.explanation = ""


# ------------------- Title -------------------
st.markdown('<div class="kbc-title">Gully Quiz League</div>', unsafe_allow_html=True)

# ------------------- Sidebar -------------------

with st.sidebar:
    st.header("Game Settings")
    st.session_state.category = st.selectbox(
        "Category",
        ["general knowledge", "science", "history", "geography", "biology", "sports"],
        index=["general knowledge","science","history","geography","biology","sports"].index(st.session_state.category),
    )
    st.session_state.difficulty = st.selectbox(
        "Difficulty",
        ["easy", "medium", "hard", "progressive"],
        index=["easy", "medium", "hard", "progressive"].index(st.session_state.difficulty),
    )

    label = "Start ▶" if st.session_state.question is None else "Next Question ▶"
    if st.button(label, type="primary", use_container_width=True):
        try:
            fetch_next_question()
        except Exception as e:
            st.error(f"Backend error: {e}")

    if st.button("Reset Score ⟲", type="secondary", use_container_width=True):
        reset_game()
        st.success("Scores reset and game cleared.")



# ------------------- Score row (Right left, spacer middle, Wrong right) -------------------
score_l, score_mid, score_r = st.columns([1, 1.2, 1])
with score_l:
    st.markdown(f'<span class="pill pill-green">Right: {st.session_state.score_right}</span>', unsafe_allow_html=True)
with score_r:
    st.markdown(f'<div style="text-align:right;"><span class="pill pill-red">Wrong: {st.session_state.score_wrong}</span></div>', unsafe_allow_html=True)

# ------------------- Question pill -------------------
st.markdown(
    f"""
    <div class="card" style="border-radius:999px; margin-top:.6rem;">
      <div class="q-text">{st.session_state.question["text"] if st.session_state.question else "Press Start ▶ to begin the game."}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)

# ------------------- Options 2×2 with inline 'Select' buttons -------------------
def render_option_row(label: str, text: str):
    is_correct = (label == st.session_state.correct)
    is_selected = (label == st.session_state.selected)

    cls = "answer-tile"
    if st.session_state.selected is not None:
        if is_selected and is_correct: cls += " answer-correct"
        elif is_selected and not is_correct: cls += " answer-wrong"
        elif is_correct: cls += " answer-correct"
        else: cls += " answer-dim"

    col_text, col_btn = st.columns([8, 1])
    with col_text:
        st.markdown(f'<div class="{cls}">{label}) {text}</div>', unsafe_allow_html=True)
    with col_btn:
        disabled = st.session_state.selected is not None
        if st.button("Select", key=f"sel_{label}", use_container_width=True, disabled=disabled):
            st.session_state.selected = label
            finalize_outcome(label)
            st.rerun()

if st.session_state.question:
    opts = st.session_state.question["options"]
    r1c1, r1c2 = st.columns(2, gap="large")
    with r1c1:
        render_option_row("A", opts["A"])
    with r1c2:
        render_option_row("B", opts["B"])

    r2c1, r2c2 = st.columns(2, gap="large")
    with r2c1:
        render_option_row("C", opts["C"])
    with r2c2:
        render_option_row("D", opts["D"])

# ------------------- Explanation -------------------
if st.session_state.question and st.session_state.selected is not None:
    if st.session_state.selected == st.session_state.correct:
        st.success("✅ Correct!")
    else:
        st.error("❌ Wrong.")
    if st.session_state.explanation:
        st.caption(f"Explanation: {st.session_state.explanation}")

# ------------------- Footer credit -------------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center; opacity:.85; font-size:.9rem;">'
    '© 2025 · A product of <b>Riyaz Shaikh Studios</b><br>'
    '<i>Let’s build something great</i>'
    '</div>',
    unsafe_allow_html=True,
)

