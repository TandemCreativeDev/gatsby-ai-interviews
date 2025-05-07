import streamlit as st
import config
from transcript_utils import initialise_session_state, render_interviews
from login import setup_admin_page

# Initialize the admin page with login
if not setup_admin_page("View Staff Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("View completed staff interview transcripts and processed data.")
st.header("Staff Transcripts")

# Initialize session state for refresh counter
initialise_session_state()

# Add role filter dropdown
staff_roles = ["All"] + config.MONGODB_STAFF_ROLES
selected_role = st.selectbox("Filter by role:", staff_roles)

# Create container for interviews
interview_container = st.container()

# Render the interviews with role filter
render_interviews(interview_container, "Staff", role=selected_role)
