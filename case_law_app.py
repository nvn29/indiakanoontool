import streamlit as st
from fpdf import FPDF
from docx import Document
import pandas as pd
import io
from PIL import Image
import requests

# --- PAGE CONFIG ---
st.set_page_config("Indian Legal Act Search Tool", ":balance_scale:", layout="centered")
try:
    st.image(Image.open("logo.png"), width=100)
except:
    st.markdown("""
        <div style='text-align:center;'>
            <h1 style='margin-bottom:0;'>⚖️ Indian Legal Act Search Tool</h1>
            <p style='font-size:16px;color:#555;'>Search and download Acts from India Code</p>
        </div>""", unsafe_allow_html=True)

state = st.session_state
state.setdefault("search_history", [])

# --- KNOWN ACTS ---
known_acts = {
    "Constitution of India": "https://legislative.gov.in/sites/default/files/COI_2024.pdf",
    "Indian Penal Code 1860": "https://www.indiacode.nic.in/repealedfileopen?rfilename=A1860-45.pdf",
    # ... (include all your other acts here)
}

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Search / Filters")
    keyword_input = st.text_input(
        "Enter a legal keyword...",
        st.selectbox("Previous Keywords", [""] + state.search_history)
    ).strip()

    if st.button("🗑️ Clear History"):
        state.search_history.clear()
        st.success("History cleared")

# --- EXPORT FUNCTIONS ---
def export_pdf(data):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Indian Legal Act Search Results", ln=True, align="C")
    for i, c in enumerate(data, 1):
        pdf.multi_cell(0, 10, f"{i}. {c['Title']}\n{c['Link']}\n")
    return pdf.output(dest="S").encode("latin1")

def export_docx(data):
    doc = Document(); doc.add_heading("Indian Legal Act Search Results", 0)
    for i, c in enumerate(data, 1):
        doc.add_paragraph(f"{i}. {c['Title']}", style="List Number")
        doc.add_paragraph(f"Link: {c['Link']}")
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

def export_excel(data):
    buf = io.BytesIO()
    pd.DataFrame(data).to_excel(buf, index=False, sheet_name="Acts", engine="xlsxwriter")
    buf.seek(0)
    return buf

# --- SEARCH RESULTS DISPLAY ---
if keyword_input:
    detected_acts = [
        act for act in known_acts
        if act.lower() in keyword_input.lower() or keyword_input.lower() in act.lower()
    ]

    results_data = []

    if detected_acts:
        st.write(f"### 📂 Search Results for keyword: `{keyword_input}`")
        for act in detected_acts:
            act_url = known_acts[act]
            st.markdown(f"### {act}")
            
            # Try fetching PDF; fallback with informative message
            try:
                pdf_data = requests.get(act_url, timeout=15).content
                st.download_button(
                    f"📄 Download PDF: {act}",
                    data=pdf_data,
                    file_name=act.replace(" ", "_") + ".pdf",
                    mime="application/pdf"
                )
            except:
                st.warning(
                    f"⚠️ Unable to fetch PDF automatically. This may be due to IndiaCode server being down. "
                    f"You can check for updates via Google News. 👉 [Open '{act}' on IndiaCode]({act_url})"
                )

            results_data.append({"Title": act, "Link": act_url})

        # Export options
        st.download_button("📄 Export PDF", export_pdf(results_data), "results.pdf", "application/pdf")
        st.download_button("📝 Export DOCX", export_docx(results_data), "results.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.download_button("📊 Export Excel", export_excel(results_data), "results.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        # Unknown keyword → dynamic India Code search link with informative message
        search_url = f"https://www.indiacode.nic.in/handle/123456789/act-search?query={keyword_input.replace(' ', '+')}"
        st.warning(
            f"⚠️ No known Act detected or IndiaCode search may be temporarily unavailable. "
            f"You can confirm the server status via Google News. 👉 [Search manually]({search_url})"
        )

    if keyword_input not in state.search_history:
        state.search_history.insert(0, keyword_input)
        state.search_history = state.search_history[:10]

else:
    st.warning("📥 Enter a legal keyword to search.")

# --- FOOTER ---
st.markdown("""
<hr style="margin-top:40px;">
<div style='text-align: center; font-size: 14px; color: gray;'>
    Created by <strong>Naveen Yadav</strong><br>
    <em>LLB(Hons) First Year, Sushant University, Gurugram</em><br>
    ⚖️ Indian Legal Act Search Tool | © 2025
</div>
""", unsafe_allow_html=True)
