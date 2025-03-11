import streamlit as st
import os
import sys
import time

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def admin_login():
    """Custom login just for admin page"""
    def login_form():
        with login_placeholder.form("Admin Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
            
            if submitted:
                # Check if username is admin and password is correct
                if (username == config.ADMIN_USERNAME and 
                    username in st.secrets.get("passwords", {}) and 
                    password == st.secrets.passwords[username]):
                    st.session_state.admin_logged_in = True
                    login_placeholder.empty()
                    return True
                else:
                    st.error("Invalid username or password")
                    return False
            return False
    
    # Check if already logged in
    if st.session_state.get("admin_logged_in", False):
        return True
        
    # Show login form
    return login_form()

def display_transcript(file_path):
    """Display a transcript file with formatting"""
    try:
        with open(file_path, "r") as f:
            transcript_text = f.read()
        
        # Display the transcript in a scrollable text area
        st.text_area("Interview Transcript", transcript_text, height=400)
    except Exception as e:
        st.error(f"Error reading transcript: {e}")

def display_time_info(file_path):
    """Display time information for an interview"""
    try:
        with open(file_path, "r") as f:
            time_info = f.read()
        
        st.info(time_info)
    except Exception as e:
        st.error(f"Error reading time information: {e}")

# Set page title and icon
st.set_page_config(page_title="Admin View | Gatsby AI Interview", page_icon="🔒")
login_placeholder = st.empty()

# Admin login - separate from regular login
if not admin_login():
    st.stop()

# Admin view header
st.title("Interview Responses Admin View")
st.write("View completed interview transcripts")
 
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

def delete_and_refresh(interview_id):
    from database import delete_interview
    if delete_interview(interview_id):
        st.success("Interview deleted successfully.")
    else:
        st.error("Failed to delete interview.")
    st.session_state.refresh_counter += 1

interview_container = st.container()

def render_interviews():
    with interview_container:
        try:
            from database import get_interviews, delete_interview
            interviews = get_interviews()
            if interviews:
                for interview in interviews:
                    st.subheader(f"Interview with {interview.get('username', 'Unknown')}")
                    st.write(f"Timestamp: {interview.get('timestamp', 'N/A')}")
                    st.text_area("Transcript", interview.get("transcript", ""), height=200)
                    # Display additional fields if available from database schema
                    if interview.get("age_range") is not None:
                        st.write(f"Age Range: {interview.get('age_range')}")
                    if interview.get("gender") is not None:
                        st.write(f"Gender: {interview.get('gender')}")
                    if interview.get("school") is not None:
                        st.write(f"School: {interview.get('school')}")
                    if interview.get("start_time") is not None:
                        st.write(f"Start Time: {interview.get('start_time')}")
                    if interview.get("end_time") is not None:
                        st.write(f"End Time: {interview.get('end_time')}")
                    if interview.get("completed") is not None:
                        st.write(f"Completed: {interview.get('completed')}")
                    if interview.get("responses") is not None:
                        st.json(interview.get("responses"), label="Responses")
                    if interview.get("sentiment_analysis") is not None:
                        st.json(interview.get("sentiment_analysis"), label="Sentiment Analysis")
                    st.button("Delete", key=str(interview.get('_id')), on_click=delete_and_refresh, args=(interview.get('_id'),))
                    st.download_button(
                        label="Download Transcript",
                        data=interview.get("transcript", ""),
                        file_name=f"{interview.get('username', 'unknown')}_transcript.txt",
                        mime="text/plain"
                    )
            else:
                st.info("No interview responses found in the database.")
        except Exception as e:
            st.error(f"Error fetching interview responses: {e}")

render_interviews()
