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

def generate_summary(query, raw_info):
    prompt = f"""You are an expert research analyst. Based on the search results below, create a comprehensive structured report.

Query: {query}

Search Results:
{raw_info[:4000]}

Generate a well-structured report with these exact sections:

## Key Points
- List 5-7 most important facts

## Important Findings
- List 4-6 significant findings or trends

## Actionable Insights
- List 3-5 specific actionable recommendations

## Summary
A 2-3 sentence executive summary

Keep it professional and factual. Remove any duplicate information. Do NOT include a references or sources section, that will be added separately."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def format_sources_section(sources):
    if not sources:
        return "\n\n## References/Sources\nNo direct source links available.\n"
    lines = ["\n\n## References/Sources"]
    for i, s in enumerate(sources[:10], 1):
        title = s.get("title", "Source")
        link = s.get("link", "")
        lines.append(f"{i}. {title} - {link}")
    return "\n".join(lines)

def export_markdown(query, summary, sources):
    filename = f"research_{query[:20].replace(' ', '_')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Research Report: {query}\n\n")
        f.write(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(summary)
        f.write(format_sources_section(sources))
    return filename

def clean_line(line):
    line = line.encode('latin-1', 'replace').decode('latin-1')
    line = re.sub(r'[^\x20-\x7E]', ' ', line)
    line = re.sub(r'\s+', ' ', line).strip()
    return line

def export_pdf(query, summary, sources):
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
    full_text = summary + format_sources_section(sources)

    for raw_line in full_text.split('\n'):
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

st.set_page_config(page_title="AI Research Agent", page_icon="🔬", layout="wide")
st.title("AI Research Agent")
st.caption("Powered by Groq LLaMA 3 + Multi-source Web Search")

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

query = st.text_input("Enter your research topic:", placeholder="e.g. Latest trends in AI automation for businesses")

if st.button("Start Research", type="primary"):
    if query:
        with st.spinner("Gathering information from multiple sources..."):
            raw_info, sources = gather_info(query)

        with st.spinner("AI analyzing and structuring the report..."):
            summary = generate_summary(query, raw_info)

        st.success("Research Complete!")
        st.markdown(summary)
        st.markdown(format_sources_section(sources))

        save_memory(query, summary, sources)

        col1, col2 = st.columns(2)

        with col1:
            md_file = export_markdown(query, summary, sources)
            with open(md_file, "r", encoding="utf-8") as f:
                st.download_button(
                    "Download Markdown",
                    f.read(),
                    file_name=md_file,
                    mime="text/markdown"
                )

        with col2:
            pdf_file = export_pdf(query, summary, sources)
            with open(pdf_file, "rb") as f:
                st.download_button(
                    "Download PDF",
                    f.read(),
                    file_name=pdf_file,
                    mime="application/pdf"
                )
    else:
        st.warning("Please enter a research topic!")