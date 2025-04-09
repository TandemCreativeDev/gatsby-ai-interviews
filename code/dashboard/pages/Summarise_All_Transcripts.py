import os
import sys

import streamlit as st

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralised login module
from login import setup_admin_page

# Initialize the admin page with login
if not setup_admin_page("Summarise All Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("Generate a summarised overview of all transcripts in a collection.")

st.header("Collection Summary")

# Import after page header setup to ensure proper error handling
import config
from database import get_database, test_connection

# Get available collections
db = get_database()
if db is not None:
    # This returns a list of collections in the database
    available_collections = test_connection()
    if not available_collections:
        st.error("No collections found in the database. Please check your MongoDB connection.")
        st.stop()
else:
    st.error("Could not connect to the database. Please check your MongoDB connection.")
    st.stop()

# Collection selection dropdown
collection_options = available_collections

selected_collection = st.selectbox(
    "Select MongoDB Collection", 
    options=collection_options,
    index=0 if collection_options else None
)
