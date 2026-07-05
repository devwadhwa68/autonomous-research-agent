import os
import json
import re
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.messages import HumanMessage
from fpdf import FPDF
import concurrent.futures

load_dotenv()

llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
search = DuckDuckGoSearchResults(output_format="list")

MEMORY_FILE = "search_history.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(query, summary, sources):
    history = load_memory()
    history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "query": query,
        "summary": summary,
        "sources": sources
    })
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def search_source(query):
    try:
        return search.run(query)
    except:
        return []

def gather_info(query):
    queries = [
        query,
        f"{query} latest news 2025",
        f"{query} analysis insights"
    ]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(search_source, queries))

    combined_text = ""
    all_sources = []
    seen_links = set()

    for result_set in results:
        if not result_set:
            continue
        for item in result_set:
            snippet = item.get("snippet", "")
            title = item.get("title", "")
            link = item.get("link", "")
            combined_text += f"{title}: {snippet}\n\n"
            if link and link not in seen_links:
                seen_links.add(link)
                all_sources.append({"title": title, "link": link})

    return combined_text, all_sources

def generate_summary(query, raw_info, sources):
    source_list = ""
    for s in sources[:10]:
        source_list += f"- {s.get('title', 'Source')}: {s.get('link', '')}\n"

    prompt = f"""You are a knowledgeable research analyst. Based on the search results below, write a clear, well-written research report on the topic, as if you're explaining it to someone in a thoughtful conversation.

Query: {query}

Search Results:
{raw_info[:4000]}

Available Sources (with their actual URLs):
{source_list}

Structure the report with 2-3 headings that are specific and relevant to this particular topic (not generic labels like "Key Points" or "Important Findings"). Under each heading, write flowing paragraphs of prose explaining that aspect of the topic. Only use a bullet or numbered list if you are genuinely listing several distinct discrete items (like naming specific products, foods, dates, or steps) — otherwise write in paragraphs.

Only cite sources that provide genuine informational content (news articles, official reports, research, industry analysis). Do not cite e-commerce product pages, shopping listings, or promotional pages that aren't providing factual information about the topic.

Whenever you state a fact that comes from one of the sources above, add a small inline markdown link right after that sentence using this exact format: [🔗](actual_url_here) — using the real URL from the source list, not a placeholder or number. Do not use numbered citations like [1].

After the topic-specific sections, add a final heading called "## Summary" with a short, clear 2-3 sentence wrap-up of the main takeaway (no links needed in the summary).

Write naturally and conversationally, like a knowledgeable person explaining the topic in an article. Remove duplicate information. Do NOT include a separate references or sources list at the end — links should only appear inline."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def clean_line(line):
    line = line.encode('latin-1', 'replace').decode('latin-1')
    line = re.sub(r'[^\x20-\x7E]', ' ', line)
    line = re.sub(r'\s+', ' ', line).strip()
    return line

def strip_links_for_pdf(text):
    return re.sub(r'\[🔗\]\([^)]*\)', '', text)

def export_markdown(query, summary):
    filename = f"research_{query[:20].replace(' ', '_')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Research Report: {query}\n\n")
        f.write(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(summary)
    return filename

def export_pdf(query, summary):
    filename = f"research_{query[:20].replace(' ', '_')}.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Research Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Query: {clean_line(query)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)

    effective_width = pdf.w - pdf.l_margin - pdf.r_margin
    text_for_pdf = strip_links_for_pdf(summary)

    for raw_line in text_for_pdf.split('\n'):
        line = clean_line(raw_line)

        if not line:
            pdf.ln(4)
            continue

        if raw_line.strip().startswith('## '):
            pdf.set_font("Helvetica", "B", 12)
            try:
                pdf.multi_cell(effective_width, 8, line.replace('## ', '').strip())
            except Exception:
                pass
            pdf.set_font("Helvetica", "", 10)
        else:
            try:
                pdf.multi_cell(effective_width, 6, line)
            except Exception:
                pass

    pdf.output(filename)
    return filename

def generate_followup_answer(chat_history, report_context, question):
    history_text = ""
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n\n"

    prompt = f"""You are a knowledgeable research analyst continuing a conversation about a research report you already wrote.

Original Research Report:
{report_context}

Conversation so far:
{history_text}

New Question: {question}

Answer the question using the context of the original report and the conversation history.

Choose the best format based on what's being asked:
- If the question asks for a list of items, options, examples, steps, foods, products, or anything where the user would benefit from scanning distinct entries (e.g. "what are some...", "list...", "which foods...", "give me options for..."), answer with a clear bullet or numbered list, with a short one-line intro sentence before it.
- If the question asks for an explanation, opinion, comparison, or analysis, answer in natural flowing paragraphs.

Be specific and reference relevant parts of the report where applicable. If the question asks for something not covered in the report, use your general knowledge but mention that it goes beyond the original research scope."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

st.set_page_config(page_title="AI Research Agent", page_icon="🔬", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="InputInstructions"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("AI Research Agent")
st.caption("Powered by Groq LLaMA 3 + Multi-source Web Search")

if "report_generated" not in st.session_state:
    st.session_state.report_generated = False
if "current_query" not in st.session_state:
    st.session_state.current_query = ""
if "current_summary" not in st.session_state:
    st.session_state.current_summary = ""
if "current_sources" not in st.session_state:
    st.session_state.current_sources = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.header("Search History")
    history = load_memory()
    if history:
        for item in reversed(history[-5:]):
            with st.expander(f"{item['timestamp']}"):
                st.write(f"**Query:** {item['query']}")
                st.write(item['summary'][:200] + "...")
    else:
        st.info("No previous searches yet.")

    st.divider()
    if st.button("Start New Research"):
        st.session_state.report_generated = False
        st.session_state.current_query = ""
        st.session_state.current_summary = ""
        st.session_state.current_sources = []
        st.session_state.chat_history = []
        st.rerun()

if not st.session_state.report_generated:
    query = st.text_input("Enter your research topic:", placeholder="e.g. Latest trends in AI automation for businesses")

    if st.button("Start Research", type="primary"):
        if query:
            with st.spinner("Gathering information from multiple sources..."):
                raw_info, sources = gather_info(query)

            with st.spinner("AI analyzing and structuring the report..."):
                summary = generate_summary(query, raw_info, sources)

            save_memory(query, summary, sources)

            st.session_state.report_generated = True
            st.session_state.current_query = query
            st.session_state.current_summary = summary
            st.session_state.current_sources = sources
            st.session_state.chat_history = []
            st.rerun()
        else:
            st.warning("Please enter a research topic!")

else:
    st.success(f"Research Complete: {st.session_state.current_query}")
    st.markdown(st.session_state.current_summary)

    col1, col2 = st.columns(2)

    with col1:
        md_file = export_markdown(
            st.session_state.current_query,
            st.session_state.current_summary
        )
        with open(md_file, "r", encoding="utf-8") as f:
            st.download_button(
                "Download Markdown",
                f.read(),
                file_name=md_file,
                mime="text/markdown"
            )

    with col2:
        pdf_file = export_pdf(
            st.session_state.current_query,
            st.session_state.current_summary
        )
        with open(pdf_file, "rb") as f:
            st.download_button(
                "Download PDF",
                f.read(),
                file_name=pdf_file,
                mime="application/pdf"
            )

    st.divider()

    for msg in st.session_state.chat_history:
        role_label = "You" if msg["role"] == "user" else "AI"
        st.markdown(f"**{role_label}:** {msg['content']}")

    with st.form(key="followup_form", clear_on_submit=True, border=False):
        col_input, col_btn = st.columns([6, 1])
        with col_input:
            followup = st.text_input("message", label_visibility="collapsed", placeholder="Message AI Research Agent...")
        with col_btn:
            submit = st.form_submit_button("Send")

    if submit and followup:
        st.session_state.chat_history.append({"role": "user", "content": followup})

        with st.spinner("Thinking..."):
            answer = generate_followup_answer(
                st.session_state.chat_history[:-1],
                st.session_state.current_summary,
                followup
            )

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()