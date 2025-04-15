from transcript_utils import (
    initialize_session_state,
    render_student_interviews
)
from login import setup_admin_page
import streamlit as st
import os
import sys

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralized login module

# Initialize the admin page with login
if not setup_admin_page("View Student Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("View completed student interview transcripts and processed data.")
st.header("Student Transcripts")

# Initialize session state for refresh counter
initialize_session_state()

# Create container for interviews
interview_container = st.container()

# Render the interviews
render_student_interviews(interview_container)
