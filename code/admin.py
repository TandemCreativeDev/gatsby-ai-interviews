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


def main():
    # Set page title and icon
    st.set_page_config(page_title="Admin View", page_icon="🔒")
    
    # Check password (displays login screen)
    pwd_correct, username = check_password()
    
    if not pwd_correct:
        st.stop()
    
    # Check if user is admin
    if username != config.ADMIN_USERNAME:
        st.error("You don't have permission to view this page.")
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