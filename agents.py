import os
import sys

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# If running outside the venv, automatically load from the project's .venv site-packages
try:
    from langchain.agents import create_agent
except ImportError:
    _venv_site = os.path.abspath(os.path.join(os.path.dirname(__file__), ".venv", "Lib", "site-packages"))
    if os.path.exists(_venv_site):
        if _venv_site not in sys.path:
            sys.path.insert(0, _venv_site)
        for _m in list(sys.modules.keys()):
            if _m.startswith("langchain") or _m.startswith("langgraph"):
                del sys.modules[_m]
        from langchain.agents import create_agent
    else:
        raise

from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import tavily_search, scrape_url, web_search

groq_api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

llm = ChatGroq(model=groq_model, temperature=0, groq_api_key=groq_api_key, max_retries=5)

# agent 1
def build_search_agent():
    return create_agent(
        model=llm,
        tools=[tavily_search],
        system_prompt=(
            "You are a web search assistant. Search the web for up-to-date and reliable information using the 'tavily_search' tool with the exact parameter 'query'. "
            "Always include the exact URLs of the sources found in your final response so downstream reader agents can scrape them."
        )
    )


# agent 2
def build_reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url, tavily_search],
        system_prompt=(
            "You are a research reader agent. Your main goal is to scrape and read content from a web URL using 'scrape_url' with parameter 'url'. "
            "If a URL is present in the text, call 'scrape_url' on it immediately. "
            "If no URL is present, call 'tavily_search' with parameter 'query' to find the relevant article URL first, then call 'scrape_url' on it."
        )
    )


writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual and professional."""),
])

writer_chain = writer_prompt | llm | StrOutputParser()

# critic_chain 
critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""),
])

critic_chain = critic_prompt | llm | StrOutputParser()
