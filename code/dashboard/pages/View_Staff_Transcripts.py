import streamlit as st
import os
import sys

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralized login module
from login import setup_admin_page
from transcript_utilities import initialize_session_state, render_staff_interviews

# Initialize the admin page with login
if not setup_admin_page("View Staff Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("View completed staff interview transcripts and processed data.")
st.header("Staff Transcripts")

# Initialize session state for refresh counter
initialize_session_state()

# Create container for interviews
interview_container = st.container()

# Render the interviews
render_staff_interviews(interview_container)