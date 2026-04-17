import streamlit as st
import uuid
import os
import hashlib
import tempfile
import time
from ai_engine import generate_section
from doc_processor import extract_doc_structure
from doc_writer import rebuild_doc

# Cache document extraction to avoid reprocessing
@st.cache_data(ttl=3600)
def cached_extract_doc_structure(file_bytes, file_hash):
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return extract_doc_structure(tmp_path)
    finally:
        os.remove(tmp_path)

# ============ PAGE CONFIG & STYLING ============
st.set_page_config(
    page_title="AI Project Report Generator",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.markdown("""
<style>
.block-container {padding: 1.5rem;}
.report-box {background-color: #ffffff; border: 1px solid #e6e9ee; border-radius: 10px; padding: 16px;}
.heading-main {font-size: 2.2rem; font-weight: 700; margin-bottom: 0.25rem;}
.subtext {color:#475569; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="report-box"><div class="heading-main">📘 AI Project Report Generator</div><div class="subtext">Generate polished project documentation from structured Word headings</div></div>', unsafe_allow_html=True)

# top-right nav buttons
if "page" not in st.session_state:
    st.session_state.page = "home"

nav_left, nav_home, nav_about, nav_profile = st.columns([6, 1, 1, 1])
with nav_left:
    st.write("")
with nav_home:
    if st.button("Home", key="nav_home"):
        st.session_state.page = "home"
with nav_about:
    if st.button("About", key="nav_about"):
        st.session_state.page = "about"
with nav_profile:
    if st.button("Profile", key="nav_profile"):
        st.session_state.page = "profile"

if st.session_state.page == "about":
    st.markdown("### About")
    st.info("This tool converts Word headers into an AI-generated project report with professional formatting.")
    st.write("- Upload a .docx with headings like Abstract, Introduction, Methodology, Results, Conclusion")
    st.write("- Use the model and creativity settings; then generate and download the final report")
    st.stop()

if st.session_state.page == "profile":
    st.markdown("### Profile")
    st.success("Logged in as: Guest User")
    st.write("User role: Viewer")
    st.write("Document generation history and settings will appear here.")
    st.stop()

# ============ SESSION STATE ============
if "generated_sections" not in st.session_state:
    st.session_state.generated_sections = None
if "structure" not in st.session_state:
    st.session_state.structure = None
if "file_hash" not in st.session_state:
    st.session_state.file_hash = None
if "output_path" not in st.session_state:
    st.session_state.output_path = None

# ============ INPUT SECTION ============
st.header("⚙️ Configuration")

with st.form("config_form"):
    project_title = st.text_input(
        "📌 Project Title",
        placeholder="e.g., Real Estate Price Prediction using ML",
        help="Enter the title of your project report"
    )
    model = st.selectbox(
        "🧠 AI Model",
        ["phi3:mini", "llama3.1:8b"],
        help="Select the AI model for content generation"
    )
    temperature = st.slider(
        "🎨 Creativity Level",
        0.1, 0.9, 0.3,
        help="Lower = factual, Higher = creative"
    )
    uploaded_file = st.file_uploader(
        "📤 Upload Word Document",
        type=["docx"],
        help="Upload a .docx file with headings"
    )

    generate = st.form_submit_button("🚀 Parse & Generate");

if generate:
    if not project_title:
        st.error("Please enter a project title.")
    elif not uploaded_file:
        st.error("Please upload a Word document.")
    else:
        st.success("Configuration loaded. Generating report... Please wait")

# ============ PROCESS UPLOAD ============
if generate and uploaded_file and project_title:
    file_bytes = uploaded_file.getbuffer().tobytes()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    # ensure clean upload directory exists
    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    output_path = os.path.join(upload_dir, f"{str(uuid.uuid4())}_output.docx")
    st.session_state.output_path = output_path

    # save the uploaded file into uploads/ directory so it is organized
    input_path = os.path.join(upload_dir, f"{str(uuid.uuid4())}_input.docx")
    with open(input_path, "wb") as f:
        f.write(file_bytes)
    st.session_state.uploaded_path = input_path

    # Only re-extract if file changed
    if st.session_state.file_hash != file_hash:
        structure = cached_extract_doc_structure(file_bytes, file_hash)
        st.session_state.structure = structure
        st.session_state.file_hash = file_hash
        st.session_state.generated_sections = None
    else:
        structure = st.session_state.structure
    
    headings = [p["text"] for p in structure if p["heading_level"]]

    if not headings:
        st.warning("No headings were detected in the uploaded document. Please use Heading styles (Heading 1/2/3) or clear section titles.")

    # Display detected sections
    st.subheader(f"✅ Detected {len(headings)} Sections:")
    for heading in headings:
        st.write(f"• {heading}")

    # Generate content (per-section, concurrent)
    if headings and st.session_state.generated_sections is None and generate:
        progress_bar = st.progress(0, text="Initializing...")
        status_text = st.empty()
        total = len(headings)

        status_text.text("⏳ Generating content (per-section requests)...")

        results = [None] * total

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _task(idx, heading):
            return idx, generate_section(
                project_title=project_title,
                heading=heading,
                model=model,
                temperature=temperature
            )

        max_workers = min(8, total) if total > 0 else 1
        failed_sections = []
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_task, i, h): i for i, h in enumerate(headings)}
            completed = 0
            for fut in as_completed(futures):
                try:
                    idx, text = fut.result()
                    results[idx] = text
                    if text.startswith("[Failed to generate content"):
                        failed_sections.append(headings[idx])
                except Exception as e:
                    results[futures[fut]] = f"[Failed to generate content for section: {headings[futures[fut]]}]"
                    failed_sections.append(headings[futures[fut]])
                completed += 1
                progress_bar.progress(completed / total, text=f"Progress: {completed}/{total}")

        if failed_sections:
            st.warning("Some sections failed to generate. Please retry or check your model/API connection.")

        st.session_state.generated_sections = results
        status_text.text("✅ Content generation complete!")
        st.balloons()
        st.rerun()

# ============ PREVIEW SECTION ============
if st.session_state.generated_sections:
    st.header(f"👀 Preview: {project_title}")
    
    headings = [p["text"] for p in st.session_state.structure if p["heading_level"]]
    
    # Create tabs for each section
    tabs = st.tabs(headings)
    
    for idx, (tab, heading, content) in enumerate(zip(tabs, headings, st.session_state.generated_sections)):
        with tab:
            st.text_area(
                label="Content",
                value=content,
                height=250,
                disabled=False,
                key=f"content_{idx}_{heading}"
            )
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("✅ Generate & Download Report", use_container_width=True, type="primary"):
            rebuild_doc(
                 project_title=project_title,
                 structure=st.session_state.structure,
                 generated_sections=st.session_state.generated_sections,
                 output_path=st.session_state.output_path,
                 template_path=st.session_state.uploaded_path
            )

            st.success("🎉 Word file generated successfully!")

            with open(st.session_state.output_path, "rb") as f:
                st.download_button(
                    "⬇️ Download Word Report",
                    f,
                    file_name="AI_Project_Report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
    
    with col3:
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.generated_sections = None
            st.session_state.structure = None
            st.session_state.file_hash = None
            st.session_state.output_path = None
            st.rerun()

# ============ SIDEBAR INFO ============
with st.sidebar:
    st.markdown("### 📋 About This Tool")
    st.info("""
    This AI-powered application helps you:
    - Upload Word documents with section headings
    - Auto-generate professional content for each section
    - Preview and edit generated content
    - Download a complete report
    """)
    
    st.markdown("### ⚙️ Settings")
    st.markdown("- **Model**: Select between different AI models")
    st.markdown("- **Creativity**: Adjust the tone from factual to creative")
    
    st.markdown("### 📞 Support")
    st.markdown("For issues or feedback, please contact the support team.")
