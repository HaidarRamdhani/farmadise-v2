import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import logging
import plotly.express as px

# Backend URL
BACKEND_URL = "https://farmadise-v2-production.up.railway.app"

# Session state
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
    st.session_state.role = None
    st.session_state.username = None

# Logging helper
def log_response(response):
    logging.info(f"Status Code: {response.status_code}")
    logging.info(f"Response Body: {response.text}")

# Login function
def login(username, password):
    response = requests.post(
        f"{BACKEND_URL}/api/login/",
        json={"username": username, "password": password}
    )
    log_response(response)
    try:
        if response.status_code == 200:
            data = response.json()
            st.session_state.access_token = data["access_token"]
            st.session_state.role = data["role"]
            st.session_state.username = username
            return True
        else:
            error_message = response.json().get("detail", "Unknown error")
            st.error(f"Login failed: {error_message}")
    except ValueError:
        st.error("Invalid response from server.")
    return False

# Signup function
def signup(username, password):
    response = requests.post(
        f"{BACKEND_URL}/api/signup/",
        json={"username": username, "password": password}
    )
    log_response(response)
    try:
        if response.status_code == 200:
            st.success("Akun berhasil dibuat! Silakan login.")
            return True
        else:
            error_message = response.json().get("detail", "Unknown error")
            st.error(f"Sign up failed: {error_message}")
    except ValueError:
        st.error("Invalid response from server.")
    return False

# Main app
def main_app():
    # Sidebar
    st.sidebar.write(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.access_token = None
        st.rerun()

    # Tabs
    tab_home, tab_profile, tab_update, tab_dashboard, tab_database = st.tabs(
        ["Home", "My Profile", "Update", "Daily Dashboard", "Database"]
    )

    # Tab Home
    with tab_home:
        st.header("Home")
        response = requests.get(f"{BACKEND_URL}/api/responses/")
        if response.status_code == 200:
            data = response.json()
            for item in reversed(data):
                st.markdown(f"""
                <div style='background-color: #333; padding: 10px; margin: 5px; border-radius: 5px;'>
                    <strong>{item['username']}</strong><br>
                    <span style='font-size: 12px;'>{item['tanggal']}</span><br>
                    {item['jawaban']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("Failed to fetch responses.")

    # Tab My Profile
    with tab_profile:
        st.header("My Profile")
        if st.session_state.username:
            st.write(f"Username: {st.session_state.username}")
            st.write(f"Role: {st.session_state.role}")
        else:
            st.warning("You are not logged in.")

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
                headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
                response = requests.post(
                    f"{BACKEND_URL}/api/responses/",
                    json={
                        "jawaban": jawaban_text,
                        "username": st.session_state.username
                    },
                    headers=headers
                )
                if response.status_code == 200:
                    st.success("Data tersimpan!")
                    st.rerun()
                else:
                    error_message = response.json().get("detail", "Unknown error")
                    st.error(f"Failed to save data: {error_message}")

    # Tab Daily Dashboard
    with tab_dashboard:
        st.header("Daily Dashboard")

        # Ambil data dari backend
        response = requests.get(f"{BACKEND_URL}/api/daily-dashboard/")
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)

            if not df.empty:
                # Visualisasi dengan Plotly
                fig = px.line(
                    df,
                    x='tanggal',
                    y='sentimen_negatif',
                    title="Frekuensi Sentimen Negatif Harian",
                    labels={'sentimen_negatif': 'Jumlah Sentimen Negatif', 'tanggal': 'Tanggal'}
                )

                # Sorot anomali
                fig.add_scatter(
                    x=df[df['anomaly'] == 1]['tanggal'],
                    y=df[df['anomaly'] == 1]['sentimen_negatif'],
                    mode='markers',
                    marker=dict(color='red', size=10),
                    name='Anomali'
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No responses found.")
        else:
            st.error("Failed to fetch dashboard data.")

    # Tab Database
    with tab_database:
        st.header("Database Overview")
        response = requests.get(f"{BACKEND_URL}/api/responses/")
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                st.write("All Records in Database:")
                st.dataframe(df)
            else:
                st.info("Database is empty.")
        else:
            st.error("Failed to fetch database data.")

# Run the app
if st.session_state.access_token:
    main_app()
else:
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if login(username, password):
                st.rerun()

    # Tambahkan tombol "Daftar di sini"
    st.write("Belum memiliki akun?")
    if st.button("Daftar di sini"):
        with st.form("signup_form"):
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            if st.form_submit_button("Sign Up"):
                if signup(new_username, new_password):
                    st.rerun()
