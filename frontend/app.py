import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

BACKEND_URL = "http://localhost:8000"  # Ganti dengan URL backend saat deploy

# Session state
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
    st.session_state.role = None
    st.session_state.username = None

def login(username, password):
    response = requests.post(
        f"{BACKEND_URL}/api/login/",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        st.session_state.access_token = data["access_token"]
        st.session_state.role = data["role"]
        st.session_state.username = username
        return True
    return False

def main_app():
    st.sidebar.write(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.access_token = None
        st.experimental_rerun()

    tab_home, tab_profile, tab_update, tab_dashboard, tab_database = st.tabs(
        ["Home", "My Profile", "Update", "Daily Dashboard", "Database"]
    )

    # Tab Home
    with tab_home:
        st.header("Home")
        response = requests.get(f"{BACKEND_URL}/api/responses/")
        data = response.json()
        for item in reversed(data):
            st.markdown(f"""
            <div style='background-color: #333; padding: 10px; margin: 5px; border-radius: 5px;'>
                <strong>{item['username']}</strong><br>
                <span style='font-size: 12px;'>{item['tanggal']}</span><br>
                {item['jawaban']}
            </div>
            """, unsafe_allow_html=True)

    # Tab Update
    with tab_update:
        st.header("Update Pesan")
        with st.form("input_form", clear_on_submit=True):
            tanggal_input = st.date_input(
                "Tanggal pengisian:",
                value=datetime.now(pytz.timezone('Asia/Jakarta')).date()
            )
            jawaban_text = st.text_area("Jawaban:")
            
            if st.form_submit_button("Kirim") and jawaban_text.strip():
                response = requests.post(
                    f"{BACKEND_URL}/api/responses/",
                    json={
                        "jawaban": jawaban_text,
                        "username": st.session_state.username
                    }
                )
                if response.status_code == 200:
                    st.success("Data tersimpan!")
                    st.experimental_rerun()

# Jalankan aplikasi
if st.session_state.access_token:
    main_app()
else:
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if login(username, password):
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")