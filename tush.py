import streamlit as st
import time
import json
import os

from ai_engine import generate_section
from doc_processor import extract_doc_structure
from doc_writer import rebuild_doc

st.set_page_config(page_title="Smart Report Generator", layout="wide", initial_sidebar_state="collapsed")

# ---------------- USER AUTH ----------------
USERS_FILE = "users.json"

@st.cache_resource
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

users = load_users()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""

def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
    load_users.clear()

@st.cache_data(ttl=600)
def verify_credentials(username: str, password: str) -> bool:
    return username in users and users[username] == password

def sign_up(username, password):
    if username in users:
        st.error("Username already exists!")
    else:
        users[username] = password
        save_users()
        st.success("Sign up successful! Please login.")

def sign_in(username, password):
    if verify_credentials(username, password):
        st.session_state.logged_in = True
        st.session_state.current_user = username
        st.success(f"Welcome, {username}!")
    else:
        st.error("Invalid username or password")

# ---------------- LOGIN / REGISTER UI ----------------
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>Sign In / Sign Up</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

    with tab1:
        st.subheader("Sign In")
        username = st.text_input("Username", key="signin_user")
        password = st.text_input("Password", type="password", key="signin_pass")
        if st.button("Sign In"):
            sign_in(username, password)
        st.write("---")

    with tab2:
        st.subheader("Sign Up")
        new_user = st.text_input("Choose Username", key="signup_user")
        new_pass = st.text_input("Choose Password", type="password", key="signup_pass")
        if st.button("Sign Up"):
            if new_user and new_pass:
                sign_up(new_user, new_pass)
            else:
                st.warning("Please enter both username and password.")
    
    st.stop()  # Stop execution until logged in

# ---------------- SESSION STATE ----------------
if "step" not in st.session_state:
    st.session_state.step = 1

if "title" not in st.session_state:
    st.session_state.title = ""

if "structure" not in st.session_state:
    st.session_state.structure = []

if "generated_sections" not in st.session_state:
    st.session_state.generated_sections = []

if "selected_section" not in st.session_state:
    st.session_state.selected_section = None

def next_step():
    if st.session_state.step < 5:
        st.session_state.step += 1

def prev_step():
    if st.session_state.step > 1:
        st.session_state.step -= 1

def reset_to_home():
    st.session_state.step = 1
    st.session_state.title = ""
    st.session_state.structure = []
    st.session_state.generated_sections = []
    st.session_state.selected_section = None

# ---------------- PROFESSIONAL CSS THEME ----------------
st.markdown("""
<style>
body { background-color: #f5f7fa; }
.app-title { text-align:center; font-size:34px; font-weight:700; color:#1f2933; }
.app-subtitle { text-align:center; font-size:15px; color:#6b7280; margin-bottom:25px; }
.step-label { text-align:center; font-size:16px; color:#2563eb; margin-bottom:18px; font-weight:600; }
.card { background:white; padding:28px; border-radius:14px; box-shadow:0 4px 12px rgba(0,0,0,0.08); max-width:950px; margin:auto; }
.section-title { font-size:20px; font-weight:600; color:#111827; margin-bottom:15px; }
.highlight { background:#e8f0fe; padding:10px; border-radius:8px; margin-bottom:8px; font-weight:600; color:#1d4ed8; }
.footer-nav { margin-top:30px; }
.stButton>button { border-radius:8px; height:44px; font-weight:600; }
.primary-btn button { background:#2563eb; color:white; }
.secondary-btn button { background:#e5e7eb; color:#111827; }
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("<div class='app-title'>Smart Report Generator</div>", unsafe_allow_html=True)
st.markdown(f"<div class='app-subtitle'>Logged in as: {st.session_state.current_user}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='step-label'>Step {st.session_state.step} of 5</div>", unsafe_allow_html=True)

# ---------------- MAIN CARD ----------------
st.markdown("<div class='card'>", unsafe_allow_html=True)

# ---------------- STEP 1 ----------------
if st.session_state.step == 1:
    st.markdown("<div class='section-title'>Enter Report Title & Upload File</div>", unsafe_allow_html=True)

    st.session_state.title = st.text_input("Report Title", value=st.session_state.title)

    uploaded = st.file_uploader("Upload DOCX Document", type=["docx"])

    if uploaded:
        # write a persistent copy of the uploaded document so we can reuse it later
        input_path = f"{str(uuid.uuid4())}_input.docx"
        with open(input_path, "wb") as f:
            f.write(uploaded.read())
        st.session_state.uploaded_path = input_path

        st.session_state.structure = extract_doc_structure(input_path)
        st.success("Document structure extracted successfully")

# ---------------- STEP 2 ----------------
elif st.session_state.step == 2:
    st.markdown("<div class='section-title'>Detected Sections</div>", unsafe_allow_html=True)

    sections = [s["text"] for s in st.session_state.structure if s["heading_level"]]

    if sections:
        selected = st.radio("Select Section", sections)
        st.session_state.selected_section = selected

        for s in sections:
            if s == selected:
                st.markdown(f"<div class='highlight'>{s}</div>", unsafe_allow_html=True)
            else:
                st.write(s)
    else:
        st.warning("No headings found in document.")

# ---------------- STEP 3 ----------------
elif st.session_state.step == 3:
    st.markdown("<div class='section-title'>Generate Content</div>", unsafe_allow_html=True)

    sections = [s["text"] for s in st.session_state.structure if s["heading_level"]]

    st.info(f"Report Title: {st.session_state.title}")
    st.info(f"Total Sections: {len(sections)}")

    if st.button("Generate All Sections"):
        st.session_state.generated_sections = []

        progress = st.progress(0)

        for i, sec in enumerate(sections):
            with st.spinner(f"Generating: {sec}"):
                text = generate_section(
                    st.session_state.title,
                    sec
                )

                st.session_state.generated_sections.append(text)

            progress.progress((i + 1) / len(sections))

        st.success("All sections generated successfully!")

# ---------------- STEP 4 ----------------
elif st.session_state.step == 4:
    st.markdown("<div class='section-title'>Preview Report</div>", unsafe_allow_html=True)

    preview_text = ""
    sections = [s["text"] for s in st.session_state.structure if s["heading_level"]]

    for sec, txt in zip(sections, st.session_state.generated_sections):
        preview_text += sec + "\n" + txt + "\n\n"

    st.text_area("Preview", preview_text, height=300)

# ---------------- STEP 5 ----------------
elif st.session_state.step == 5:
    st.markdown("<div class='section-title'>Download Report</div>", unsafe_allow_html=True)

    if st.button("Build Final Report"):
        rebuild_doc(
            st.session_state.title,
            st.session_state.structure,
            st.session_state.generated_sections,
            "final_report.docx"
        )

        st.success("Report created successfully!")

    try:
        with open("final_report.docx", "rb") as f:
            st.download_button(
                "Download Report",
                f,
                "Smart_Report.docx"
            )
        
        st.divider()
        if st.button("🏠 Back to Home", key="home_btn"):
            reset_to_home()
            st.rerun()
    except:
        st.info("Click Build Final Report first")

# ---------------- NAVIGATION ----------------
st.markdown("<div class='footer-nav'>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,2,1])

with col1:
    if st.session_state.step > 1:
        st.markdown("<div class='secondary-btn'>", unsafe_allow_html=True)
        st.button("Back", on_click=prev_step)
        st.markdown("</div>", unsafe_allow_html=True)

with col3:
    if st.session_state.step < 5:
        st.markdown("<div class='primary-btn'>", unsafe_allow_html=True)
        st.button("Next", on_click=next_step)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
