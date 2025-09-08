import streamlit as st, requests, pandas as pd, io, re
from bs4 import BeautifulSoup
from fpdf import FPDF
from docx import Document
from PIL import Image

# --- PAGE CONFIG ---
st.set_page_config("Indian Case Law & Act Search Tool", ":balance_scale:", layout="centered")
try:
    st.image(Image.open("logo.png"), width=100)
except:
    st.markdown("""
        <div style='text-align:center;'>
            <h1 style='margin-bottom:0;'>⚖️ Indian Case Law & Act Search Tool</h1>
            <p style='font-size:16px;color:#555;'>Smart filters and act detection</p>
        </div>""", unsafe_allow_html=True)

state = st.session_state
state.setdefault("search_history", [])

known_acts = [
    "Indian Penal Code", "Code of Criminal Procedure", "Indian Evidence Act",
    "Hindu Marriage Act", "Special Marriage Act", "Contract Act",
    "Transfer of Property Act", "Consumer Protection Act",
    "Arbitration and Conciliation Act", "Companies Act", "Income Tax Act",
    "Information Technology Act", "Motor Vehicles Act", "Environment Protection Act"
]

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Search Filters")
    keyword_input = st.text_input(
        "🔍 Type keyword...",
        st.selectbox("📚 Previous Keywords", [""] + state.search_history)
    ).strip()

    for ma in [a for a in known_acts if keyword_input.lower() in a.lower() and keyword_input]:
        if st.button(ma):
            keyword_input, st.session_state["keyword"] = ma, ma
            st.rerun()

    keyword = keyword_input
    court = st.selectbox("⚖️ Court", [
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
    year_range = st.slider("📅 Year Range", 1950, 2025, (1950, 2025))
    ipc_filter_enabled = st.checkbox("📘 IPC-only")

    districts = ["All"] + [
        "Gurgaon", "Rewari", "Pune", "Mumbai", "Bangalore", "Chennai", "Delhi",
        "Lucknow", "Hyderabad", "Kolkata", "Jaipur", "Ahmedabad", "Bhopal",
        "Patna", "Indore", "Kanpur"
    ]
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

# --- EXPORTS ---
def export_pdf(data):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Indian Case Law & Act Results", ln=True, align="C")
    for i, c in enumerate(data, 1):
        pdf.multi_cell(0, 10, f"{i}. {c['Title']} | {c.get('Court','-')} ({c.get('Year','-')})\n{c['Link']}\n")
    return pdf.output(dest="S").encode("latin1")

def export_docx(data):
    doc = Document(); doc.add_heading("Indian Case Law & Act Results", 0)
    for i, c in enumerate(data, 1):
        doc.add_paragraph(f"{i}. {c['Title']} | {c.get('Court','-')} ({c.get('Year','-')})", style="List Number")
        doc.add_paragraph(f"Link: {c['Link']}")
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

def export_excel(data):
    buf = io.BytesIO()
    pd.DataFrame(data).to_excel(buf, index=False, sheet_name="Cases", engine="xlsxwriter")
    buf.seek(0)
    return buf

# --- SEARCH (India Code) ---
def search_indiacode(keyword):
    """
    Search India Code for Acts matching a keyword.
    Returns a list of Acts with title and URL.
    """
    base_url = "https://www.indiacode.nic.in/"
    search_url = f"https://www.indiacode.nic.in/handle/123456789/15?query={keyword.replace(' ', '+')}"
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    
    res = requests.get(search_url, headers=headers, timeout=15)
    if res.status_code != 200:
        st.error(f"⚠️ Could not fetch data from India Code. Status: {res.status_code}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    acts = []

    # Find all links containing the keyword in text
    for link in soup.find_all("a", href=True):
        if keyword.lower() in link.text.lower():
            act_url = base_url + link['href']
            acts.append({
                "Title": link.text.strip(),
                "Link": act_url,
                "Court": "-", "Year": "-"
            })
    return acts

# --- SEARCH EXECUTION ---
if keyword:
    st.write(f"### 📂 Search Results for: `{keyword}`")
    with st.spinner("🔎 Fetching from India Code..."):
        try:
            acts_found = search_indiacode(keyword)
            if not acts_found:
                st.info("No Acts found matching your keyword.")
            else:
                st.success(f"✅ {len(acts_found)} Act(s) found")
                for i, act in enumerate(acts_found, 1):
                    st.markdown(f"### {i}. {act['Title']}")
                    st.markdown(f"🔗 [View Act]({act['Link']})")
                    # Optional: add download button for PDF
                    pdf_filename = act['Title'].replace(' ', '_') + ".pdf"
                    try:
                        pdf_response = requests.get(act['Link'], timeout=15)
                        st.download_button(
                            f"📄 Download PDF: {act['Title']}",
                            data=pdf_response.content,
                            file_name=pdf_filename,
                            mime="application/pdf"
                        )
                    except:
                        st.warning("PDF not available for direct download.")

                # Export buttons
                if keyword not in state.search_history:
                    state.search_history.insert(0, keyword)
                    state.search_history = state.search_history[:10]

                st.download_button("📄 Export PDF", export_pdf(acts_found), "results.pdf", "application/pdf")
                st.download_button("📝 Export DOCX", export_docx(acts_found), "results.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                st.download_button("📊 Export Excel", export_excel(acts_found), "results.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"⚠️ Search failed: {e}")
            st.exception(e)
else:
    st.warning("📥 Enter a keyword to search.")

# --- FOOTER ---
st.markdown("""
<hr style="margin-top:40px;">
<div style='text-align: center; font-size: 14px; color: gray;'>
    Created by <strong>Naveen Yadav</strong><br>
    <em>LLB(Hons) First Year, Sushant University, Gurugram</em><br>
    ⚖️ Indian Case Law & Act Search Tool | © 2025
</div>
""", unsafe_allow_html=True)
