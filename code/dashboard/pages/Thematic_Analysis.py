from thematic_analytics import (
    extract_user_prompts,
    preprocess_text,
    extract_key_terms,
    identify_themes_with_keywords,
    generate_ai_thematic_analysis,
    format_keyword_themes
)
from login import setup_admin_page
from database import get_database, test_connection
import config
import sys
import os
import streamlit as st
from datetime import datetime

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralised login module

# Import our thematic analysis functions

# Initialize the admin page with login
if not setup_admin_page("Thematic Analysis | Gatsby AI Interview"):
    st.stop()

st.write("Generate thematic analysis of interview transcripts with focus on emerging patterns.")

st.header("Transcript Thematic Analysis")

# Get available collections
db = get_database()
if db is not None:
    # This returns a list of collections in the database
    available_collections = test_connection()
    if not available_collections:
        error_msg = ("No collections found in the database. "
                     "Please check your MongoDB connection.")
        st.error(error_msg)
        raise ValueError(error_msg)
else:
    error_msg = ("Could not connect to the database. "
                 "Please check your MongoDB connection.")
    st.error(error_msg)
    raise ValueError(error_msg)

# Collection selection dropdown
collection_options = available_collections

selected_collection = st.selectbox(
    "Select MongoDB Collection",
    options=collection_options,
    index=0 if collection_options else None
)

# Add staff role filter if staff collection is selected
selected_role = None
if selected_collection and "staff" in selected_collection.lower():
    from database import get_staff_roles
    staff_roles = get_staff_roles()
    selected_role = st.selectbox("Filter by role:", staff_roles)

# Analysis type
analysis_type = st.radio(
    "Analysis Type",
    ["Keyword-Based Analysis", "AI-Generated Thematic Analysis"],
    help="Choose between a faster keyword-based analysis or a more comprehensive AI-generated analysis"
)

# Process button to retrieve the interviews
if st.button("Retrieve and Analyse"):
    if selected_collection:
        with st.spinner("Retrieving interviews..."):
            # Get the database
            db = get_database()
            if db is not None:
                # Access the collection directly
                collection = db[selected_collection]

                # Create filter query
                filter_query = {}

                # Apply role filter for staff collections
                if "staff" in selected_collection.lower() and selected_role and selected_role != "All":
                    filter_query["role"] = selected_role

                # Query documents with filter
                documents = list(collection.find(filter_query))

                if documents:
                    st.session_state['interviews'] = documents

                    # Display count of retrieved documents with role info if applicable
                    role_info = ""
                    if "staff" in selected_collection.lower() and selected_role and selected_role != "All":
                        role_info = f" with role '{selected_role}'"

                    st.success(
                        f"Successfully retrieved {len(documents)} interviews{role_info} "
                        f"from the '{selected_collection}' collection.")

                    # Process based on selected analysis type
                    if analysis_type == "Keyword-Based Analysis":
                        with st.spinner("Performing keyword-based thematic analysis..."):
                            # Perform keyword-based analysis
                            theme_data = identify_themes_with_keywords(
                                documents)
                            markdown_report = format_keyword_themes(theme_data)

                            # Store and display results
                            st.session_state['thematic_analysis'] = markdown_report
                            st.markdown(markdown_report)

                            # Add download button
                            st.download_button(
                                label="Download Thematic Analysis",
                                data=markdown_report,
                                file_name="keyword_thematic_analysis.md",
                                mime="text/markdown"
                            )
                    else:  # AI-Generated Analysis
                        with st.spinner("Generating AI thematic analysis (this may take a few minutes)..."):
                            # Generate AI thematic analysis
                            ai_analysis = generate_ai_thematic_analysis(
                                documents)

                            # Store and display results
                            st.session_state['thematic_analysis'] = ai_analysis
                            st.markdown(ai_analysis)

                            # Add download button
                            st.download_button(
                                label="Download AI Thematic Analysis",
                                data=ai_analysis,
                                file_name="ai_thematic_analysis.md",
                                mime="text/markdown"
                            )
                else:
                    st.warning(
                        f"No interviews found in the "
                        f"'{selected_collection}' collection.")
    else:
        st.error("Please select a collection to analyze.")

# Add explanatory information about thematic analysis
st.sidebar.markdown("""
### About Thematic Analysis

This page offers two approaches to thematic analysis:

**1. Keyword-Based Analysis**
- Fast, automated identification of themes using predefined keywords
- Consistent counting methodology for reproducible results
- Shows frequency ranges aligned with the rest of the analysis

**2. AI-Generated Thematic Analysis**
- More nuanced identification of emerging themes using NLP
- Includes verbatim quotes and deeper contextual understanding
- Follows the structure requested by Daniel:
  - Theme identification
  - Theme descriptions
  - Example quotations
  - Interpretive commentary
  - Research implications

Choose the approach that best meets your current needs.
""")
