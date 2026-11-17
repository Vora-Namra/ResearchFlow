

import html
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
    page_title="Research Flow",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

ICONS = {
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "read": '<path d="M2 4h6a4 4 0 0 1 4 4v12a3 3 0 0 0-3-3H2z"/><path d="M22 4h-6a4 4 0 0 0-4 4v12a3 3 0 0 1 3-3h7z"/>',
    "write": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "review": '<path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><path d="M22 4 12 14l-3-3"/>',
}

STAGES = [
    ("Search", "Finds recent, reliable sources", "search"),
    ("Read", "Scrapes the most relevant page", "read"),
    ("Write", "Drafts the full report", "write"),
    ("Review", "Critic checks the draft", "review"),
]

EXAMPLES = ["Solid-state batteries", "CRISPR in agriculture", "Open-source LLMs"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@500;600;700;800&display=swap');

:root {
  --bg: #0A0E1A;
  --surface: #11182B;
  --surface-2: #172138;
  --line: #243050;
  --ink: #EAEEF9;
  --body: #C9D1E6;
  --muted: #8591B3;
  --accent: #7C8CFF;
  --accent-2: #A97BFF;
  --good: #3DE0C0;
  --warn: #F5B544;
  --bad: #FF6B7A;
  --font-ui: 'Inter', 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif;
  --font-display: 'Sora', 'Inter', 'Segoe UI', system-ui, sans-serif;
}

/* Fonts: applied to text elements only, so Streamlit's icon font keeps working */
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp button, .stApp a, .stApp td, .stApp th, .stApp caption, .stMarkdown, .stCaption {
  font-family: var(--font-ui);
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { font-family: var(--font-display); letter-spacing: -0.01em; }

.stApp {
  color: var(--body);
  background:
    radial-gradient(900px 420px at 12% -8%, rgba(124,140,255,.20), transparent 60%),
    radial-gradient(700px 380px at 92% 0%, rgba(169,123,255,.14), transparent 60%),
    var(--bg);
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.6rem; padding-bottom: 4rem; max-width: 1120px; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] { background: #0D1324; border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] > div { padding-top: 1.2rem; }
.brand { display: flex; align-items: center; gap: .7rem; margin-bottom: .5rem; }
.brand .mark {
  width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: #fff;
  box-shadow: 0 6px 20px rgba(124,140,255,.35);
}
.brand .mark svg { width: 19px; height: 19px; }
.brand .title { font-family: var(--font-display); font-weight: 700; font-size: 1.08rem; color: var(--ink); line-height: 1.1; }
.brand .sub { font-size: .76rem; color: var(--muted); margin-top: 2px; }
.side-note { color: var(--muted); font-size: .84rem; line-height: 1.6; margin: .9rem 0 1.2rem; }
.side-head { font-weight: 600; font-size: .8rem; color: var(--muted); margin: 1.5rem 0 .55rem; }
section[data-testid="stSidebar"] .stButton > button {
  width: 100%; justify-content: flex-start; text-align: left; border-radius: 10px;
  background: transparent; border: 1px solid var(--line); color: var(--body);
  font-weight: 500; font-size: .85rem; padding: .5rem .8rem; transition: all .15s ease;
}
section[data-testid="stSidebar"] .stButton > button:hover { border-color: var(--accent); color: var(--ink); background: rgba(124,140,255,.08); }

/* ---------- Hero ---------- */
.hero h1 {
  font-family: var(--font-display); font-weight: 700; font-size: 3.05rem; line-height: 1.1;
  letter-spacing: -0.03em; margin: 0 0 .9rem; padding: 0;
  background: linear-gradient(120deg, #FFFFFF 10%, #C9CEFF 55%, #B79CFF 100%);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p { color: var(--muted); font-size: 1.06rem; max-width: 58ch; line-height: 1.65; margin: 0 0 1.8rem; }

/* ---------- Inputs ---------- */
.stTextInput [data-baseweb="input"], .stTextInput [data-baseweb="base-input"] {
  background: var(--surface); border-radius: 14px; border: 1px solid var(--line);
  transition: border-color .15s ease, box-shadow .15s ease;
}
.stTextInput [data-baseweb="input"]:focus-within {
  border-color: var(--accent); box-shadow: 0 0 0 4px rgba(124,140,255,.18);
}
.stTextInput input {
  background: transparent; color: var(--ink); font-size: 1.04rem; padding: .95rem 1.05rem;
  -webkit-text-fill-color: var(--ink);
}
.stTextInput input::placeholder { color: var(--muted); -webkit-text-fill-color: var(--muted); opacity: 1; }

.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #6F80FF, #A06BFF); color: #fff; border: none;
  font-weight: 600; font-size: .98rem; border-radius: 14px; padding: .86rem 1.2rem; width: 100%;
  box-shadow: 0 8px 24px rgba(124,140,255,.32); transition: transform .12s ease, box-shadow .12s ease, filter .12s ease;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover {
  filter: brightness(1.08); box-shadow: 0 10px 30px rgba(124,140,255,.42); color: #fff;
}
.stButton > button[kind="primary"]:active { transform: translateY(1px); }

.stButton > button[kind="secondary"], .stButton > button[data-testid="stBaseButton-secondary"] {
  border-radius: 999px; border: 1px solid var(--line); background: var(--surface);
  color: var(--muted); font-size: .8rem; font-weight: 500; padding: .3rem .95rem; white-space: nowrap;
}
.stButton > button[kind="secondary"]:hover, .stButton > button[data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--accent); color: var(--ink);
}

/* ---------- Pipeline tracker ---------- */
.tracker-wrap {
  background: linear-gradient(180deg, var(--surface), #0F1629); border: 1px solid var(--line);
  border-radius: 22px; padding: 1.6rem 1.6rem 1.4rem; margin: 2rem 0 1rem;
}
.tracker { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; }
.step { padding-right: .9rem; }
.rail { display: flex; align-items: center; margin-bottom: .95rem; }
.node {
  width: 46px; height: 46px; border-radius: 50%; display: grid; place-items: center; flex: none;
  background: var(--surface-2); border: 1.5px solid var(--line); color: var(--muted);
}
.node svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.line { flex: 1; height: 2px; margin: 0 10px; background: var(--line); border-radius: 2px; }
.step:last-child .line { display: none; }
.step .name { font-family: var(--font-display); font-weight: 600; font-size: 1rem; color: var(--ink); }
.step .desc { color: var(--muted); font-size: .82rem; margin-top: .3rem; line-height: 1.5; }
.step .state { font-size: .8rem; font-weight: 600; margin-top: .75rem; color: var(--muted); }

.step.run .node { border-color: var(--accent); color: var(--accent); background: rgba(124,140,255,.12); animation: glow 1.5s ease-in-out infinite; }
.step.run .line { background: linear-gradient(90deg, var(--accent), var(--line) 70%); }
.step.run .state { color: var(--accent); }
.step.done .node { border-color: var(--good); color: var(--good); background: rgba(61,224,192,.10); }
.step.done .line { background: var(--good); }
.step.done .state { color: var(--good); }
.step.error .node { border-color: var(--bad); color: var(--bad); background: rgba(255,107,122,.10); }
.step.error .state { color: var(--bad); }

@keyframes glow { 0%,100% { box-shadow: 0 0 0 0 rgba(124,140,255,.5); } 50% { box-shadow: 0 0 0 9px rgba(124,140,255,0); } }
@media (prefers-reduced-motion: reduce) { .step.run .node { animation: none; } }
@media (max-width: 820px) {
  .tracker { grid-template-columns: 1fr 1fr; row-gap: 1.4rem; }
  .step:nth-child(2) .line { display: none; }
  .hero h1 { font-size: 2.2rem; }
}

/* ---------- Result header ---------- */
.result-title { font-family: var(--font-display); font-size: 1.9rem; font-weight: 700; letter-spacing: -0.02em; color: var(--ink); margin: 1.8rem 0 .9rem; }
.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .8rem; margin-bottom: 1.4rem; }
.stat { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: .85rem 1.1rem; }
.stat b { display: block; font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; color: var(--ink); }
.stat span { font-size: .8rem; color: var(--muted); }
@media (max-width: 640px) { .stats { grid-template-columns: 1fr; } }

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap: .4rem; border-bottom: 1px solid var(--line); padding-bottom: 0; }
.stTabs button[data-baseweb="tab"] {
  background: transparent; color: var(--muted); font-weight: 600; font-size: .92rem;
  padding: .65rem 1rem; border-radius: 10px 10px 0 0;
}
.stTabs button[data-baseweb="tab"]:hover { color: var(--ink); background: rgba(124,140,255,.07); }
.stTabs button[aria-selected="true"] { color: var(--ink); }
.stTabs [data-baseweb="tab-highlight"] { background: linear-gradient(90deg, var(--accent), var(--accent-2)); height: 3px; border-radius: 3px; }
.stTabs [data-baseweb="tab-border"] { background: transparent; }

/* ---------- Content panels ---------- */
.st-key-report, .st-key-critic, .st-key-sources, .st-key-scraped {
  background: var(--surface); border: 1px solid var(--line); border-radius: 18px;
  padding: 1.8rem 2.1rem; margin-top: 1.1rem;
}
.st-key-critic { border-left: 4px solid var(--warn); }
.st-key-report [data-testid="stMarkdownContainer"] { max-width: 80ch; }
.st-key-report p, .st-key-report li, .st-key-critic p, .st-key-critic li {
  font-size: 1.02rem; line-height: 1.8; color: var(--body);
}
.st-key-report h1, .st-key-report h2, .st-key-report h3, .st-key-critic h1, .st-key-critic h2, .st-key-critic h3 { color: var(--ink); }
.st-key-report h1 { font-size: 1.7rem; }
.st-key-report h2 { font-size: 1.3rem; margin-top: 1.8rem; padding-top: .4rem; }
.st-key-report h3 { font-size: 1.08rem; }
.st-key-report strong { color: var(--ink); }
.stApp a { color: var(--good); text-decoration: none; }
.stApp a:hover { text-decoration: underline; }
.stApp blockquote { border-left: 3px solid var(--accent); background: rgba(124,140,255,.07); padding: .4rem 1rem; border-radius: 0 10px 10px 0; }
.stApp code { background: var(--surface-2); color: #D8DEFF; border-radius: 6px; padding: .1rem .35rem; }
.stApp table { border-collapse: collapse; }
.stApp th, .stApp td { border: 1px solid var(--line); padding: .5rem .8rem; }
.stApp th { background: var(--surface-2); color: var(--ink); }
.stApp hr { border-color: var(--line); }

/* ---------- Misc ---------- */
.empty {
  border: 1.5px dashed var(--line); border-radius: 20px; padding: 2.2rem 1.8rem; margin-top: 1.6rem;
  color: var(--muted); font-size: .95rem; line-height: 1.7; background: rgba(17,24,43,.5);
}
.empty b { color: var(--ink); font-family: var(--font-display); font-size: 1.05rem; }
div[data-testid="stAlert"] { border-radius: 14px; border: 1px solid var(--line); background: var(--surface-2); }
.stDownloadButton > button {
  border-radius: 12px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); font-weight: 600;
}
.stDownloadButton > button:hover { border-color: var(--accent); color: var(--ink); }
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
        parts = [b.get("text", "") if isinstance(b, dict) else str(b) for b in content]
        return "\n".join(p for p in parts if p)
    return str(content)


def tracker_html(status, timings):
    labels = {"wait": "Waiting", "run": "Working...", "done": "Done", "error": "Failed"}
    steps = []
    for i, (name, desc, icon) in enumerate(STAGES):
        s = status[i]
        state = f"Done in {timings[i]:.1f}s" if s == "done" and i in timings else labels[s]
        steps.append(
            f'<div class="step {s}"><div class="rail"><div class="node">'
            f'<svg viewBox="0 0 24 24">{ICONS[icon]}</svg></div><div class="line"></div></div>'
            f'<div class="name">{name}</div><div class="desc">{desc}</div>'
            f'<div class="state">{state}</div></div>'
        )
    return '<div class="tracker-wrap"><div class="tracker">' + "".join(steps) + "</div></div>"


def run_pipeline(topic: str, tracker_slot, note_slot) -> dict:
    status = ["wait"] * 4
    timings: dict[int, float] = {}
    state: dict = {}

    def refresh():
        tracker_slot.markdown(tracker_html(status, timings), unsafe_allow_html=True)

    def on_wait(seconds, attempt, maximum):
        note_slot.info(f"Rate limit reached. Retrying in {seconds:.0f}s (attempt {attempt} of {maximum}).")

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

    def do_search():
        agent = build_search_agent()
        res = invoke_with_retry(
            agent,
            {"messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]},
            on_wait=on_wait,
        )
        return as_text(res["messages"][-1].content)

    state["search_results"] = run_stage(0, do_search)

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

    def do_write():
        combined = (
            f"SEARCH RESULTS : \n {state['search_results']} \n\n"
            f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
        )
        return as_text(invoke_with_retry(writer_chain, {"topic": topic, "research": combined}, on_wait=on_wait))

    state["report"] = run_stage(2, do_write)

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


def new_research():
    st.session_state.current = None
    st.session_state.topic_input = ""


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'{ICONS["search"]}</svg></div><div><div class="title">Research Flow</div>'
        '<div class="sub">Multi-agent research</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="side-note">One agent searches, one reads the best page, one writes the report '
        "and one reviews it.</div>",
        unsafe_allow_html=True,
    )
    st.button("New research", key="new_research", on_click=new_research)
    st.markdown('<div class="side-head">Past reports</div>', unsafe_allow_html=True)
    if st.session_state.history:
        for i in range(len(st.session_state.history) - 1, -1, -1):
            t = st.session_state.history[i]["topic"]
            st.button(t if len(t) <= 32 else t[:30] + "…", key=f"hist_{i}", on_click=load_run, args=(i,))
    else:
        st.caption("Reports from this session will appear here.")


# ----------------------------------------------------------------------------
# Hero + input
# ----------------------------------------------------------------------------
st.markdown(
    '<div class="hero"><h1>Ask a question. Get a researched report.</h1>'
    "<p>Enter any topic. Four agents search the web, read the best source, write the report "
    "and review it, and you can watch each step as it runs.</p></div>",
    unsafe_allow_html=True,
)

col_in, col_btn = st.columns([5, 1.25], vertical_alignment="bottom")
with col_in:
    topic = st.text_input(
        "Research topic",
        key="topic_input",
        placeholder="e.g. Impact of AI on drug discovery",
        label_visibility="collapsed",
    )
with col_btn:
    start = st.button("Start research", type="primary", use_container_width=True)

ex_cols = st.columns([1.05, 1.2, 1.05, 2.4])
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
    if not start:
        st.markdown(
            '<div class="empty"><b>No report yet</b><br>Enter a topic above or pick an example, '
            "then select Start research. A run usually takes a few minutes, and longer if the "
            "model rate limit is reached.</div>",
            unsafe_allow_html=True,
        )
else:
    if not start:
        tracker_slot.markdown(tracker_html(["done"] * 4, current["timings"]), unsafe_allow_html=True)

    words = len(current["report"].split())
    st.markdown(
        f'<div class="result-title">{html.escape(current["topic"])}</div>'
        f'<div class="stats">'
        f'<div class="stat"><b>{words:,}</b><span>Words in report</span></div>'
        f'<div class="stat"><b>{current["total"]:.0f}s</b><span>Total time</span></div>'
        f'<div class="stat"><b>{current["finished_at"]}</b><span>Completed</span></div>'
        f"</div>",
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
    st.write("")
    d1, d2, _ = st.columns([1.4, 1.8, 4])
    d1.download_button(
        "Download report", current["report"], file_name=f"{slug}.md", mime="text/markdown",
        key=f"dl_report_{current['finished_at']}",
    )
    d2.download_button(
        "Download with review", full_doc, file_name=f"{slug}-full.md", mime="text/markdown",
        key=f"dl_full_{current['finished_at']}",
    )