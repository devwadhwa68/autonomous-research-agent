# Autonomous Research Agent

🔗 **Live Demo:** https://autonomous-research-agent-ensb4nbbcfyolueuzsw3ab.streamlit.app/

An autonomous AI agent that searches multiple external sources for a given topic...

An autonomous AI agent that searches multiple external sources for a given topic, analyzes the results, removes duplicates, and generates a structured, actionable research report with references — built using LangChain, Groq (LLaMA 3.1), and Streamlit.

## Features

- Accepts any user query/topic as input
- Autonomously searches multiple external sources in parallel (DuckDuckGo)
- Extracts and deduplicates relevant information
- Uses an LLM (Groq LLaMA 3.1) to reason over the raw data and generate a structured report:
  - Key Points
  - Important Findings
  - Actionable Insights
  - References/Sources
- Stores previous searches in local memory (JSON) for future reference
- Exports the final report as Markdown or PDF
- Simple web interface built with Streamlit

## Tech Stack

- **Python 3.10+**
- **Streamlit** – web interface
- **LangChain + langchain-groq** – LLM orchestration
- **Groq API (LLaMA 3.1-8B-Instant)** – reasoning and summarization
- **DuckDuckGo Search (langchain-community)** – external information retrieval
- **FPDF2** – PDF report generation
- **concurrent.futures** – parallel multi-source searching

## How It Works

1. User enters a research topic in the Streamlit UI.
2. The agent autonomously generates multiple search queries around the topic and searches them in parallel.
3. Search results are collected, deduplicated, and passed to the LLM.
4. The LLM reasons over the raw information (no hardcoded rules or static templates) and produces a structured report.
5. Source links are extracted separately and appended as a References section.
6. The report is displayed in the UI, saved to search history, and can be exported as Markdown or PDF.

## Installation Steps

1. **Clone the repository**