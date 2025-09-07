import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io, re, random
from fpdf import FPDF
from docx import Document
from PIL import Image

# --- Page Config ---
st.set_page_config("Indian Case Law Search Tool", ":balance_scale:", layout="centered")

# --- Header / Logo ---
try:
    st.image(Image.open("logo.png"), width=100)
except:
    st.markdown("""
        <div style='text-align:center;'>
            <h1 style='margin-bottom:0;'>⚖️ Indian Case Law Search Tool</h1>
            <p style='font-size:16px;color:#555;'>Smart filters and act detection</p>
        </div>""", unsafe_allow_html=True)

# --- Session State ---
state = st.session_state
state.setdefault("search_history", [])

# --- Known Acts ---
known_acts = [
    "Indian Penal Code", "Code of Criminal Procedure", "Indian Evidence Act",
    "Hindu Marriage Act", "Special Marriage Act", "Contract Act",
    "Transfer of Property Act", "Consumer Protection Act",
    "Arbitration and Conciliation Act", "Companies Act", "Income Tax Act",
    "Information Technology Act", "Motor Vehicles Act", "Environment Protection Act"
]

# --- Sidebar Filters ---
with st.sidebar:
    st.header("🔍 Search Filters")
    keyword_input = st.text_input(
        "Type keyword...", st.selectbox("Previous Keywords", [""] + state.search_history)
    ).strip()

    # Smart suggestions for known acts
    for act in [a for a in known_acts if keyword_input.lower() in a.lower() and keyword_input]:
        if st.button(act):
            keyword_input = act
            st.session_state["keyword"] = act
            st.rerun()

    keyword = keyword_input

    court = st.selectbox("⚖️ Court", [
        "All Courts", "Supreme Court", "Allahabad High Court",
        "Bombay High Court", "Calcutta High Court", "Delhi High Court",
        "Madras High Court", "Punjab & Haryana High Court",
        "Rajasthan High Court", "Kerala High Court"
    ])

    year_range = st.slider("📅 Year Range", 1950, 2025, (1950, 2025))
    ipc_filter_enabled = st.checkbox("📘 IPC-only")

    districts = ["All", "Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Jaipur", "Lucknow"]
    auto_detected = next((d for d in districts if d.lower() in keyword.lower()), None)
    default_index = districts.index(auto_detected) if auto_detected in districts else 0

    if court == "All Courts":
        district = None
    else:
        district_option = st.selectbox("🏛️ District", districts, index=default_index)
        district = None if district_option == "All" else district_option

    if st.button("🗑️ Clear History"):
        state.search_history.clear()
        st.success("History cleared")

# --- Exports ---
def export_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Indian Case Law Results", ln=True, align="C")
    for i, c in enumerate(data, 1):
        pdf.multi_cell(0, 10, f"{i}. {c['Title']}, {c['Court']} ({c['Year']})\n{c['Link']}\n")
    return pdf.output(dest="S").encode("latin1")

def export_docx(data):
    doc = Document()
    doc.add_heading("Indian Case Law Results", 0)
    for i, c in enumerate(data, 1):
        doc.add_paragraph(f"{i}. {c['Title']}, {c['Court']} ({c['Year']})", style="List Number")
        doc.add_paragraph(f"Link: {c['Link']}")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def export_excel(data):
    buf = io.BytesIO()
    pd.DataFrame(data).to_excel(buf, index=False, sheet_name="Cases", engine="xlsxwriter")
    buf.seek(0)
    return buf

# --- User Agents for rotation ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/119.0",
]

# --- Scraping Function ---
def search_scrape(keyword, pagenum=0):
    url = f"https://indiankanoon.org/search/?formInput={keyword}&pagenum={pagenum}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        res = requests.get(url, headers=headers, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        cases = []
        for div in soup.select("div.result_title"):
            title = div.get_text(strip=True)
            link = "https://indiankanoon.org" + div.a["href"]

            # Extract year if present
            year_match = re.search(r'\b(19|20)\d{2}\b', title)
            year = int(year_match.group()) if year_match else "-"

            # Extract snippet
            snippet_tag = div.find_next("div", class_="snippet")
            snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""

            # Detected Acts
            acts_found = [act for act in known_acts if act.lower() in snippet.lower()]

            # Apply filters
            if year != "-" and not (year_range[0] <= int(year) <= year_range[1]):
                continue
            if court != "All Courts" and court.lower() not in snippet.lower():
                continue
            if district and district.lower() not in title.lower():
                continue
            if ipc_filter_enabled and "ipc" not in snippet.lower():
                continue

            cases.append({
                "Title": title,
                "Link": link,
                "Year": year,
                "Court": court,
                "Bluebook Citation": f"{title}, {court} ({year})",
                "APA Citation": f"{court}. ({year}). {title}. Retrieved from {link}",
                "Detected Acts": ", ".join(acts_found) or "None"
            })
        return cases
    except Exception as e:
        st.error(f"Scraping failed on page {pagenum}: {e}")
        return []

# --- Main Search ---
if keyword:
    st.write(f"### 📂 Search Results for: `{keyword}`")
    cases = search_scrape(keyword)
    if not cases:
        st.info("No results found.")
    else:
        st.success(f"✅ {len(cases)} case(s) found")
        for i, c in enumerate(cases, 1):
            with st.expander(f"{i}. {c['Title']} ({c['Year']})"):
                st.markdown(f"**🏛️ Court**: {c['Court']}")
                st.markdown(f"**📘 Acts**: {c['Detected Acts']}")
                st.markdown(f"🔗 [View Case]({c['Link']})")
                st.caption(f"📘 Bluebook: {c['Bluebook Citation']}")
                st.caption(f"📚 APA: {c['APA Citation']}")

        # Update search history
        if keyword not in state.search_history:
            state.search_history.insert(0, keyword)
            state.search_history = state.search_history[:10]

        # Download buttons
        st.download_button("📄 PDF", export_pdf(cases), "case_results.pdf", "application/pdf")
        st.download_button("📝 DOCX", export_docx(cases), "case_results.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.download_button("📊 Excel", export_excel(cases), "case_results.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.warning("📥 Enter a keyword to search.")

# --- Footer ---
st.markdown("""
<hr style="margin-top:40px;">
<div style='text-align: center; font-size: 14px; color: gray;'>
    Created by <strong>Naveen Yadav</strong><br>
    <em>LLB(Hons) First Year, Sushant University, Gurugram</em><br>
    ⚖️ Indian Case Law Search Tool | © 2025
</div>
""", unsafe_allow_html=True)
