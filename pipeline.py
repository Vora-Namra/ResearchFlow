"""
Research Desk - Streamlit frontend for the multi-agent research system.

Save next to main.py and agents.py, then run:
    streamlit run app.py

Note: main.py is NOT imported here, because its virtual-environment re-launch
block would restart the process under Streamlit. The pipeline steps are
reproduced below with live progress hooks instead.
"""

import os
import re
import sys
import time
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain  # noqa: E402


# ----------------------------------------------------------------------------
# Page setup
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Research Desk",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

STAGES = [
    ("Search", "Finds recent, reliable sources"),
    ("Read", "Scrapes the most relevant page"),
    ("Write", "Drafts the full report"),
    ("Review", "Critic checks the draft"),
]

EXAMPLES = [
    "Solid-state battery progress",
    "How CRISPR is used in agriculture",
    "State of open-source LLMs",
]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap');

:root {
  --bg: #F4F6FA;
  --surface: #FFFFFF;
  --ink: #101828;
  --muted: #667085;
  --line: #E4E7EC;
  --accent: #2F4BDB;
  --accent-soft: #E9EDFD;
  --done: #12805C;
  --done-soft: #E3F4EC;
  --error: #C0392B;
}

html, body, [class*="st-"], .stApp { font-family: 'Manrope', sans-serif; }
.stApp { background: var(--bg); color: var(--ink); }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.4rem; max-width: 1100px; }

/* Sidebar */
section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] .stButton > button {
  text-align: left; justify-content: flex-start; width: 100%;
  background: transparent; border: 1px solid var(--line); color: var(--ink);
  border-radius: 10px; font-weight: 500; font-size: 0.86rem; padding: 0.5rem 0.75rem;
}
section[data-testid="stSidebar"] .stButton > button:hover { border-color: var(--accent); color: var(--accent); }
.side-title { font-weight: 800; font-size: 1.05rem; letter-spacing: -0.01em; margin-bottom: 0.2rem; }
.side-sub { color: var(--muted); font-size: 0.84rem; line-height: 1.5; margin-bottom: 1.2rem; }
.side-head { font-weight: 700; font-size: 0.8rem; color: var(--muted); margin: 1.4rem 0 0.5rem; }

/* Hero */
.hero h1 {
  font-family: 'Newsreader', serif; font-weight: 500; font-size: 3.1rem;
  line-height: 1.08; letter-spacing: -0.02em; margin: 0 0 0.6rem; color: var(--ink);
}
.hero p { color: var(--muted); font-size: 1.05rem; max-width: 56ch; line-height: 1.6; margin: 0 0 1.6rem; }

/* Inputs */
.stTextInput input {
  background: var(--surface); border: 1.5px solid var(--line); border-radius: 12px;
  padding: 0.85rem 1rem; font-size: 1.02rem; color: var(--ink);
}
.stTextInput input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.stButton > button[kind="primary"] {
  background: var(--accent); border: none; color: #fff; font-weight: 700;
  border-radius: 12px; padding: 0.8rem 1.4rem; width: 100%;
}
.stButton > button[kind="primary"]:hover { background: #2640C0; color: #fff; }
.stButton > button[kind="secondary"] {
  border-radius: 999px; border: 1px solid var(--line); background: var(--surface);
  color: var(--muted); font-size: 0.82rem; font-weight: 500; padding: 0.25rem 0.9rem;
}
.stButton > button[kind="secondary"]:hover { border-color: var(--accent); color: var(--accent); }

/* Pipeline tracker - the one memorable element */
.tracker { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.9rem; margin: 1.8rem 0 1rem; }
.stage {
  background: var(--surface); border: 1px solid var(--line); border-top: 4px solid var(--line);
  border-radius: 14px; padding: 1rem 1.1rem 1.05rem;
}
.stage .name { font-weight: 700; font-size: 1rem; display: flex; align-items: center; gap: 0.55rem; }
.stage .desc { color: var(--muted); font-size: 0.82rem; margin-top: 0.3rem; line-height: 1.45; }
.stage .state { font-size: 0.8rem; font-weight: 600; margin-top: 0.7rem; color: var(--muted); }
.dot { width: 9px; height: 9px; border-radius: 50%; background: var(--line); display: inline-block; }
.stage.run { border-top-color: var(--accent); }
.stage.run .dot { background: var(--accent); animation: pulse 1.2s ease-in-out infinite; }
.stage.run .state { color: var(--accent); }
.stage.done { border-top-color: var(--done); }
.stage.done .dot { background: var(--done); }
.stage.done .state { color: var(--done); }
.stage.error { border-top-color: var(--error); }
.stage.error .dot { background: var(--error); }
.stage.error .state { color: var(--error); }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(47,75,219,.45); } 50% { box-shadow: 0 0 0 7px rgba(47,75,219,0); } }
@media (prefers-reduced-motion: reduce) { .stage.run .dot { animation: none; } }
@media (max-width: 800px) { .tracker { grid-template-columns: 1fr 1fr; } .hero h1 { font-size: 2.2rem; } }

/* Result header */
.result-head { margin: 1.6rem 0 0.4rem; }
.result-head .topic { font-family: 'Newsreader', serif; font-size: 2rem; font-weight: 500; letter-spacing: -0.015em; }
.facts { display: flex; gap: 2rem; flex-wrap: wrap; margin: 0.6rem 0 1rem; color: var(--muted); font-size: 0.85rem; }
.facts b { color: var(--ink); font-weight: 700; font-size: 1.05rem; display: block; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 1.4rem; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { font-weight: 600; color: var(--muted); padding: 0.6rem 0; }
.stTabs [aria-selected="true"] { color: var(--accent); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--accent); }

/* Report body */
.st-key-report, .st-key-critic, .st-key-sources, .st-key-scraped {
  background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
  padding: 1.6rem 2rem; margin-top: 1rem;
}
.st-key-report p, .st-key-report li, .st-key-critic p, .st-key-critic li {
  font-family: 'Newsreader', serif; font-size: 1.1rem; line-height: 1.75; color: #1D2939;
}
.st-key-report h1, .st-key-report h2, .st-key-report h3 { font-family: 'Manrope', sans-serif; letter-spacing: -0.01em; color: var(--ink); }
.st-key-report h2 { font-size: 1.35rem; margin-top: 1.6rem; }
.st-key-critic { border-left: 4px solid var(--accent); }

/* Empty state */
.empty {
  border: 1.5px dashed var(--line); border-radius: 16px; padding: 2rem 1.6rem; margin-top: 1.4rem;
  color: var(--muted); font-size: 0.95rem; line-height: 1.65; background: rgba(255,255,255,.6);
}
.empty b { color: var(--ink); }

.stDownloadButton > button { border-radius: 10px; border: 1px solid var(--line); font-weight: 600; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Pipeline helpers
# ----------------------------------------------------------------------------
def invoke_with_retry(runnable, input_data, max_attempts=5, on_wait=None):
    """Invoke a LangChain runnable, retrying on Groq rate limits."""
    for attempt in range(max_attempts):
        try:
            return runnable.invoke(input_data)
        except Exception as e:  # noqa: BLE001
            err_msg = str(e)
            if any(x in err_msg for x in ["rate_limit_exceeded", "429", "413", "tokens per minute"]):
                m = re.search(r"try again in ([\d\.]+)s", err_msg)
                wait_time = float(m.group(1)) + 1.0 if m else 15.0
                if on_wait:
                    on_wait(wait_time, attempt + 1, max_attempts)
                time.sleep(wait_time)
            else:
                raise
    return runnable.invoke(input_data)


def as_text(content) -> str:
    """Normalise model output (string or list of content blocks) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            else:
                parts.append(str(block))
        return "\n".join(p for p in parts if p)
    return str(content)


def tracker_html(status, timings):
    labels = {"wait": "Waiting", "run": "Working...", "done": "Done", "error": "Failed"}
    cards = []
    for i, (name, desc) in enumerate(STAGES):
        s = status[i]
        state = labels[s]
        if s == "done" and i in timings:
            state = f"Done in {timings[i]:.1f}s"
        cards.append(
            f'<div class="stage {s}"><div class="name"><span class="dot"></span>{name}</div>'
            f'<div class="desc">{desc}</div><div class="state">{state}</div></div>'
        )
    return '<div class="tracker">' + "".join(cards) + "</div>"


def run_pipeline(topic: str, tracker_slot, note_slot) -> dict:
    status = ["wait"] * 4
    timings: dict[int, float] = {}
    state: dict = {}

    def refresh():
        tracker_slot.markdown(tracker_html(status, timings), unsafe_allow_html=True)

    def on_wait(seconds, attempt, maximum):
        note_slot.info(
            f"The model hit its rate limit. Retrying in {seconds:.0f}s (attempt {attempt} of {maximum})."
        )

    def run_stage(idx, fn):
        status[idx] = "run"
        refresh()
        started = time.time()
        try:
            out = fn()
        except Exception:
            status[idx] = "error"
            refresh()
            raise
        timings[idx] = time.time() - started
        status[idx] = "done"
        note_slot.empty()
        refresh()
        return out

    refresh()
    t0 = time.time()

    # 1. Search
    def do_search():
        agent = build_search_agent()
        res = invoke_with_retry(
            agent,
            {"messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]},
            on_wait=on_wait,
        )
        return as_text(res["messages"][-1].content)

    state["search_results"] = run_stage(0, do_search)

    # 2. Read
    def do_read():
        agent = build_reader_agent()
        res = invoke_with_retry(
            agent,
            {"messages": [(
                "user",
                f"Based on the following search results about '{topic}', "
                f"pick the most relevant URL and scrape it for deeper content.\n\n"
                f"Search Results:\n{state['search_results']}",
            )]},
            on_wait=on_wait,
        )
        return as_text(res["messages"][-1].content)

    state["scraped_content"] = run_stage(1, do_read)

    # 3. Write
    def do_write():
        combined = (
            f"SEARCH RESULTS : \n {state['search_results']} \n\n"
            f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
        )
        return as_text(invoke_with_retry(writer_chain, {"topic": topic, "research": combined}, on_wait=on_wait))

    state["report"] = run_stage(2, do_write)

    # 4. Review
    def do_review():
        return as_text(invoke_with_retry(critic_chain, {"report": state["report"]}, on_wait=on_wait))

    state["feedback"] = run_stage(3, do_review)

    state["topic"] = topic
    state["timings"] = timings
    state["total"] = time.time() - t0
    state["finished_at"] = datetime.now().strftime("%d %b %Y, %H:%M")
    return state


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
st.session_state.setdefault("history", [])
st.session_state.setdefault("current", None)
st.session_state.setdefault("topic_input", "")


def set_topic(value: str):
    st.session_state.topic_input = value


def load_run(index: int):
    st.session_state.current = st.session_state.history[index]


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="side-title">Research Desk</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="side-sub">Four agents work in sequence: one searches, one reads, '
        "one writes and one reviews.</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-head">Past reports</div>', unsafe_allow_html=True)
    if st.session_state.history:
        for i in range(len(st.session_state.history) - 1, -1, -1):
            run = st.session_state.history[i]
            label = run["topic"] if len(run["topic"]) <= 34 else run["topic"][:32] + "…"
            st.button(label, key=f"hist_{i}", on_click=load_run, args=(i,))
    else:
        st.caption("Reports from this session will appear here.")


# ----------------------------------------------------------------------------
# Hero + input
# ----------------------------------------------------------------------------
st.markdown(
    '<div class="hero"><h1>Research any topic, with a source trail.</h1>'
    "<p>Type a topic and the agents will search the web, read the best page, write a report "
    "and have it reviewed. You can follow each step as it runs.</p></div>",
    unsafe_allow_html=True,
)

col_in, col_btn = st.columns([5, 1.2], vertical_alignment="bottom")
with col_in:
    topic = st.text_input(
        "Research topic",
        key="topic_input",
        placeholder="e.g. Impact of AI on drug discovery",
        label_visibility="collapsed",
    )
with col_btn:
    start = st.button("Start research", type="primary", use_container_width=True)

ex_cols = st.columns(len(EXAMPLES) + 2)
for i, ex in enumerate(EXAMPLES):
    ex_cols[i].button(ex, key=f"ex_{i}", on_click=set_topic, args=(ex,))

tracker_slot = st.empty()
note_slot = st.empty()

# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------
if start:
    if not topic.strip():
        st.warning("Enter a topic first.")
    else:
        try:
            result = run_pipeline(topic.strip(), tracker_slot, note_slot)
            st.session_state.history.append(result)
            st.session_state.current = result
        except Exception as e:  # noqa: BLE001
            st.error(f"The pipeline stopped: {e}")

# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
current = st.session_state.current

if current is None:
    st.markdown(
        '<div class="empty"><b>Nothing here yet.</b><br>Enter a topic above, or pick one of the '
        "examples, then select Start research. A full run usually takes a few minutes, "
        "longer if the model rate limit is reached.</div>",
        unsafe_allow_html=True,
    )
else:
    if not start:
        tracker_slot.markdown(tracker_html(["done"] * 4, current["timings"]), unsafe_allow_html=True)

    words = len(current["report"].split())
    st.markdown(
        f'<div class="result-head"><div class="topic">{current["topic"]}</div>'
        f'<div class="facts">'
        f'<span><b>{words:,}</b>words in report</span>'
        f'<span><b>{current["total"]:.0f}s</b>total time</span>'
        f'<span><b>{current["finished_at"]}</b>completed</span>'
        f"</div></div>",
        unsafe_allow_html=True,
    )

    tab_report, tab_critic, tab_sources, tab_scraped = st.tabs(
        ["Report", "Critic review", "Search results", "Scraped page"]
    )

    with tab_report:
        with st.container(key="report"):
            st.markdown(current["report"])

    with tab_critic:
        with st.container(key="critic"):
            st.markdown(current["feedback"])

    with tab_sources:
        with st.container(key="sources"):
            st.markdown(current["search_results"])

    with tab_scraped:
        with st.container(key="scraped"):
            st.markdown(current["scraped_content"])

    slug = re.sub(r"[^a-z0-9]+", "-", current["topic"].lower()).strip("-")[:50] or "report"
    full_doc = (
        f"# {current['topic']}\n\n{current['report']}\n\n---\n\n"
        f"## Critic review\n\n{current['feedback']}\n\n---\n\n"
        f"## Search results\n\n{current['search_results']}\n"
    )
    d1, d2, _ = st.columns([1.3, 1.6, 4])
    d1.download_button(
        "Download report", current["report"], file_name=f"{slug}.md", mime="text/markdown",
        key=f"dl_report_{current['finished_at']}",
    )
    d2.download_button(
        "Download with review", full_doc, file_name=f"{slug}-full.md", mime="text/markdown",
        key=f"dl_full_{current['finished_at']}",
    )