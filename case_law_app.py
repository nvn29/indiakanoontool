import streamlit as st, requests, pandas as pd, io, re
from bs4 import BeautifulSoup
from fpdf import FPDF
from docx import Document
from PIL import Image

st.set_page_config("Indian Case Law Search Tool", ":balance_scale:", layout="centered")
try: st.image(Image.open("logo.png"), width=100)
except: st.markdown("""
    <div style='text-align:center;'>
        <h1 style='margin-bottom:0;'>⚖️ Indian Case Law Search Tool</h1>
        <p style='font-size:16px;color:#555;'>Smart filters and act detection</p>
    </div>""", unsafe_allow_html=True)

state = st.session_state; state.setdefault("search_history", [])
known_acts = [
    "Indian Penal Code", "Code of Criminal Procedure", "Indian Evidence Act",
    "Hindu Marriage Act", "Special Marriage Act", "Contract Act",
    "Transfer of Property Act", "Consumer Protection Act",
    "Arbitration and Conciliation Act", "Companies Act", "Income Tax Act",
    "Information Technology Act", "Motor Vehicles Act", "Environment Protection Act"]

with st.sidebar:
    st.header("🔍 Search Filters")
    keyword_input = st.text_input("🔍 Type keyword...", st.selectbox("📚 Previous Keywords", [""] + state.search_history)).strip()
    for ma in [a for a in known_acts if keyword_input.lower() in a.lower() and keyword_input]:
        if st.button(ma): keyword_input, st.session_state["keyword"] = ma, ma; st.rerun()

    keyword, court = keyword_input, st.selectbox("⚖️ Court", [
        "All Courts", "Supreme Court",
        "Allahabad High Court", "Andhra Pradesh High Court", "Bombay High Court",
        "Calcutta High Court", "Chhattisgarh High Court", "Delhi High Court",
        "Gauhati High Court", "Gujarat High Court", "Himachal Pradesh High Court",
        "Jammu & Kashmir and Ladakh High Court", "Jharkhand High Court", "Karnataka High Court",
        "Kerala High Court", "Madhya Pradesh High Court", "Madras High Court",
        "Manipur High Court", "Meghalaya High Court", "Orissa High Court",
        "Patna High Court", "Punjab & Haryana High Court", "Rajasthan High Court",
        "Sikkim High Court", "Telangana High Court", "Tripura High Court",
        "Uttarakhand High Court"
    ])
    year_range, ipc_filter_enabled = st.slider("📅 Year Range", 1950, 2025, (1950, 2025)), st.checkbox("📘 IPC-only")

    districts = ["All"] + ["Gurgaon", "Rewari", "Pune", "Mumbai", "Bangalore", "Chennai", "Delhi", "Lucknow", "Hyderabad", "Kolkata", "Jaipur", "Ahmedabad", "Bhopal", "Patna", "Indore", "Kanpur"]
    auto_detected = next((d for d in districts if d.lower() in keyword.lower()), None)
    default_index = districts.index(auto_detected) if auto_detected in districts else 0
    if court == "All Courts":
        st.info("📌 District disabled when 'All Courts' selected.")
        district = None
    else:
        district_option = st.selectbox("🏛️ District", districts, index=default_index)
        district = None if district_option == "All" else district_option

    if st.button("🗑️ Clear History"): state.search_history.clear(); st.success("History cleared")

# --- EXPORTS ---
def export_pdf(data):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Indian Case Law Results", ln=True, align="C")
    for i, c in enumerate(data, 1): pdf.multi_cell(0, 10, f"{i}. {c['Title']}, {c['Court']} ({c['Year']})\n{c['Link']}\n")
    return pdf.output(dest="S").encode("latin1")

def export_docx(data):
    doc = Document(); doc.add_heading("Indian Case Law Results", 0)
    for i, c in enumerate(data, 1):
        doc.add_paragraph(f"{i}. {c['Title']}, {c['Court']} ({c['Year']})", style="List Number")
        doc.add_paragraph(f"Link: {c['Link']}")
    buf = io.BytesIO(); doc.save(buf); buf.seek(0); return buf

def export_excel(data):
    buf = io.BytesIO(); pd.DataFrame(data).to_excel(buf, index=False, sheet_name="Cases", engine="xlsxwriter")
    buf.seek(0); return buf

# --- SEARCH ---
if keyword:
    st.write(f"### 📂 Search Results for: `{keyword}`")
    with st.spinner("🔎 Fetching from Indian Kanoon..."):
        res = requests.get(f"https://indiankanoon.org/search/?formInput={keyword}")
        if res.status_code != 200: st.error("⚠️ Could not fetch data.")
        else:
            soup = BeautifulSoup(res.text, "html.parser")
            results, cases = soup.find_all("div", class_="result_title"), []
            for result in results[:20]:
                title, link = result.get_text(strip=True), "https://indiankanoon.org" + result.find("a")["href"]
                snippet_div = result.find_next_sibling("div")
                snippet = snippet_div.get_text(strip=True) if snippet_div else ""
                year_match = re.search(r'\b(19|20)\d{2}\b', snippet)
                year = int(year_match.group()) if year_match else None
                if year and not (year_range[0] <= year <= year_range[1]): continue
                if court != "All Courts" and court.lower().split(" high court")[0] not in snippet.lower() and court.lower() not in snippet.lower(): continue
                if district and district.lower() not in title.lower(): continue
                if ipc_filter_enabled and "IPC" not in snippet.upper(): continue
                acts_found = [act for act in known_acts if act.lower() in snippet.lower()]
                cases.append({
                    "Title": title, "Link": link, "Year": year or "-", "Court": court,
                    "Bluebook Citation": f"{title}, {court} ({year})",
                    "APA Citation": f"{court}. ({year}). {title}. Retrieved from {link}",
                    "Detected Acts": ", ".join(acts_found) or "None"
                })
            if not cases:
                st.info("No results found.")
            else:
                st.success(f"✅ {len(cases)} case(s) found")
                for i, c in enumerate(cases, 1):
                    st.markdown(f"### {i}. {c['Title']}")
                    st.markdown(f"**📅 Year**: {c['Year']} | **🏛️ Court**: {c['Court']} | **📘 Acts**: {c['Detected Acts']}")
                    st.markdown(f"🔗 [View Case]({c['Link']})")
                    st.caption(f"📘 Bluebook: {c['Bluebook Citation']}")
                    st.caption(f"📚 APA: {c['APA Citation']}")
                if keyword not in state.search_history:
                    state.search_history.insert(0, keyword)
                    state.search_history = state.search_history[:10]
                st.download_button("📄 PDF", export_pdf(cases), "case_results.pdf", "application/pdf")
                st.download_button("📝 DOCX", export_docx(cases), "case_results.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                st.download_button("📊 Excel", export_excel(cases), "case_results.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.warning("📥 Enter a keyword to search.")

st.markdown("""
<hr style="margin-top:40px;">
<div style='text-align: center; font-size: 14px; color: gray;'>
    Created by <strong>Naveen Yadav</strong><br>
    <em>LLB(Hons) First Year, Sushant University, Gurugram</em><br>
    ⚖️ Indian Case Law Search Tool | © 2025
</div>
""", unsafe_allow_html=True)