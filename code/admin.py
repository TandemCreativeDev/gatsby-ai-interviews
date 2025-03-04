import streamlit as st
import os
import config
from utils import check_password


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


def admin_login():
    """Custom login just for admin page"""
    def login_form():
        with st.form("Admin Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
            
            if submitted:
                # Check if username is admin and password is correct
                if (username == config.ADMIN_USERNAME and 
                    username in st.secrets.get("passwords", {}) and 
                    password == st.secrets.passwords[username]):
                    st.session_state.admin_logged_in = True
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

def main():
    # Set page title and icon
    st.set_page_config(page_title="Admin View", page_icon="🔒")
    
    # Admin login - separate from regular login
    if not admin_login():
        st.stop()
    
    # Admin view header
    st.title("Interview Responses Admin View")
    st.write("View completed interview transcripts")
    
    # Get list of completed interviews
    transcript_files = []
    
    try:
        transcript_files = [
            f for f in os.listdir(config.TRANSCRIPTS_DIRECTORY) 
            if os.path.isfile(os.path.join(config.TRANSCRIPTS_DIRECTORY, f))
        ]
    except Exception as e:
        st.error(f"Error accessing transcripts directory: {e}")
    
    if not transcript_files:
        st.warning("No interview transcripts found.")
        return
    
    # Extract usernames from filenames
    usernames = [f.replace(".txt", "") for f in transcript_files]
    
    # Create a dropdown to select which interview to view
    selected_user = st.selectbox(
        "Select an interview to view:", 
        usernames
    )
    
    if selected_user:
        transcript_path = os.path.join(config.TRANSCRIPTS_DIRECTORY, f"{selected_user}.txt")
        time_path = os.path.join(config.TIMES_DIRECTORY, f"{selected_user}.txt")
        
        # Display interview metadata
        st.subheader(f"Interview with {selected_user}")
        
        # Display time information if available
        if os.path.exists(time_path):
            display_time_info(time_path)
        
        # Display the transcript
        display_transcript(transcript_path)
        
        # Option to download the transcript
        with open(transcript_path, "r") as f:
            transcript_text = f.read()
            
        st.download_button(
            label="Download Transcript",
            data=transcript_text,
            file_name=f"{selected_user}_transcript.txt",
            mime="text/plain"
        )


if __name__ == "__main__":
    main()