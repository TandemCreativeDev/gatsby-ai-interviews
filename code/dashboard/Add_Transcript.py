import streamlit as st
import os
import sys

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralized login module
from login import setup_admin_page

# Initialize the admin page with login
if not setup_admin_page("Add Transcript | Gatsby AI Interview"):
    st.stop()

st.write("Add interview transcripts and data manually.")

st.header("Manual Transcript Upload")
type_radio = st.radio("Type", options=["Student", "Staff"])
role = None

with st.form("upload_transcript_form"):
    username = st.text_input("Name")
    st.write(f"Type: {type_radio}")

    if type_radio == "Staff":
        role = st.selectbox("Role", options=["principal", "teacher", "office"])

    college = st.text_input("College")
    tags_text = st.text_input("Tags (comma separated)")
    start_date = st.date_input("Start Date")
    start_time_input = st.time_input("Start Time")
    end_date = st.date_input("End Date")
    end_time_input = st.time_input("End Time")
    transcript = st.text_area("Transcript")
    submit = st.form_submit_button("Upload Transcript")

if submit:
    import datetime
    try:
        start_datetime = datetime.datetime.combine(
            start_date, start_time_input)
        end_datetime = datetime.datetime.combine(end_date, end_time_input)
        time_data = {}
        time_data["start_time"] = start_datetime.timestamp()
        time_data["end_time"] = end_datetime.timestamp()
        time_data["duration"] = time_data["end_time"] - time_data["start_time"]
        if username == "":
            username = f"user_{start_datetime.strftime('%Y_%m_%d_%H_%M_%S')}"
        document = {
            "username": username,
            "transcript": transcript,
            "college": college,
            "tags": [
                tag.strip() for tag in tags_text.split(",") if tag.strip()
            ],
            "time_data": time_data,
        }
        if type_radio == "Staff":
            document["role"] = role
        from database import save_interview
        if save_interview(document, type_radio, update_if_exists=False):
            st.success("Transcript uploaded successfully.")
        else:
            st.error("Failed to upload transcript.")
    except Exception as e:
        st.error(f"Error uploading transcript: {e}")
