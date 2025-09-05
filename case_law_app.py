import streamlit as st
import requests, pandas as pd, io, re
from fpdf import FPDF
from docx import Document
from PIL import Image

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

    court = st.selectbox("⚖️ Court", ["All Courts","Supreme Court","Allahabad High Court",
        "Andhra Pradesh High Court","Bombay High Court","Calcutta High Court","Chhattisgarh High Court",
        "Delhi High Court","Gauhati High Court","Gujarat High Court","Himachal Pradesh High Court",
        "Jammu & Kashmir and Ladakh High Court","Jharkhand High Court","Karnataka High Court",
        "Kerala High Court","Madhya Pradesh High Court","Madras High Court","Manipur High Court",
        "Meghalaya High Court","Orissa High Court","Patna High Court","Punjab & Haryana High Court",
        "Rajasthan High Court","Sikkim High Court","Telangana High Court","Tripura High Court",
        "Uttarakhand High Court"])

    year_range = st.slider("📅 Year Range", 1950, 2025, (1950, 2025))
    ipc_filter_enabled = st.checkbox("📘 IPC-only")

    districts = ["All","Gurgaon","Rewari","Pune","Mumbai","Bangalore","Chennai","Delhi",
                 "Lucknow","Hyderabad","Kolkata","Jaipur","Ahmedabad","Bhopal","Patna","Indore","Kanpur"]
    auto_detected = next((d for d in districts if d.lower() in keyword.lower()), None)
    default_index = districts.index(auto_detected) if auto_detected in districts else 0

    if court == "All Courts":
        st.info("📌 District disabled when 'All Courts' selected.")
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
    pdf.cell(200,10,"Indian Case Law Results",ln=True,align="C")
    for i,c in enumerate(data,1):
        pdf.multi_cell(0,10,f"{i}. {c['Title']}, {c['Court']} ({c['Year']})\n{c['Link']}\n")
    return pdf.output(dest="S").encode("latin1")

def export_docx(data):
    doc = Document()
    doc.add_heading("Indian Case Law Results",0)
    for i,c in enumerate(data,1):
        doc.add_paragraph(f"{i}. {c['Title']}, {c['Court']} ({c['Year']})",style="List Number")
        doc.add_paragraph(f"Link: {c['Link']}")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def export_excel(data):
    buf = io.BytesIO()
    pd.DataFrame(data).to_excel(buf,index=False,sheet_name="Cases",engine="xlsxwriter")
    buf.seek(0)
    return buf

# --- Helper: broaden keyword by removing year ---
def broaden_keyword(kw):
    return re.sub(r'\b\d{4}\b', '', kw).strip()

# --- API Token ---
KANNOON_API_TOKEN = st.secrets["KANNOON_API_TOKEN"]
HEADERS = {
    "Authorization": f"Token {KANNOON_API_TOKEN}",
    "Accept": "application/json"
}

# --- API Search Function ---
def search_api(keyword, pagenum=0):
    url = f"https://api.indiankanoon.org/search/?formInput={keyword}&pagenum={pagenum}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        res.raise_for_status()
        data = res.json()
        cases=[]
        for c in data.get("docs", []):
            title = c.get("title", "")
            link = f"https://indiankanoon.org/doc/{c.get('tid','')}/"
            snippet = c.get("snippet","")
            year_match = re.search(r'\b(19|20)\d{2}\b', snippet)
            year = int(year_match.group()) if year_match else "-"
            acts_found = [act for act in known_acts if act.lower() in snippet.lower()]

            # Apply filters
            if year != "-" and not (year_range[0] <= int(year) <= year_range[1]):
                continue
            if court != "All Courts" and court.lower() not in snippet.lower():
                continue
            if district and district.lower() not in title.lower():
                continue
            if ipc_filter_enabled and "IPC" not in snippet.upper():
                continue

            cases.append({
                "Title": title, "Link": link, "Year": year, "Court": court,
                "Bluebook Citation": f"{title}, {court} ({year})",
                "APA Citation": f"{court}. ({year}). {title}. Retrieved from {link}",
                "Detected Acts": ", ".join(acts_found) or "None"
            })
        return cases
    except Exception as e:
        st.error(f"API Request Failed on page {pagenum}: {e}")
        return []

# --- Main Search ---
if keyword:
    st.write(f"### 📂 Search Results for: `{keyword}`")
    cases = search_api(keyword)
    # If no results, try broader keyword
    if not cases:
        keyword_broad = broaden_keyword(keyword)
        if keyword_broad != keyword:
            st.info(f"No exact results. Searching broader keyword: `{keyword_broad}`")
            cases = search_api(keyword_broad)

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
