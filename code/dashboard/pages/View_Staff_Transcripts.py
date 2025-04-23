from transcript_utils import initialise_session_state, render_interviews
from login import setup_admin_page
import os
import sys

import streamlit as st

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralized login module

# Initialize the admin page with login
if not setup_admin_page("View Staff Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("View completed staff interview transcripts and processed data.")
st.header("Staff Transcripts")

# Initialize session state for refresh counter
initialise_session_state()

# Create container for interviews
interview_container = st.container()

# Render the interviews
render_interviews(interview_container, "Staff")
