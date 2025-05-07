from transcript_utils import initialise_session_state, render_interviews
from login import setup_admin_page
import streamlit as st
import config

# Initialize the admin page with login
if not setup_admin_page("View Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("View completed interview transcripts and processed data.")
st.header("Interview Transcripts")

# Initialize session state for refresh counter
initialise_session_state()

# Create tabs for Student and Staff
tab_names = list(config.MONGODB_COLLECTION_NAME.keys())
tab1, tab2 = st.tabs(tab_names)

# Student tab
with tab1:
    # Create container for student interviews
    student_container = st.container()

    # Render the student interviews
    render_interviews(student_container, tab_names[0])

# Staff tab
with tab2:
    # Add role filter dropdown
    staff_roles = ["All"] + config.MONGODB_STAFF_ROLES
    selected_role = st.selectbox("Filter by role:", staff_roles)

    # Create container for staff interviews
    staff_container = st.container()

    # Render the staff interviews with role filter
    render_interviews(staff_container, tab_names[1], role=selected_role)
