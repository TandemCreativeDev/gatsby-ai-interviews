from keyword_analysis import (
    identify_themes_with_keywords,
    format_keyword_themes,
    load_keyword_data
)
from themes_analysis import generate_ai_thematic_analysis

from login import setup_admin_page
from database import get_database
import config
import streamlit as st

# Initialize the admin page with login
if not setup_admin_page("Thematic Analysis | Gatsby AI Interview"):
    st.stop()

st.write("Generate thematic analysis of interview transcripts with focus on emerging patterns.")


st.header("Transcript Thematic Analysis")
available_collections = list(config.MONGODB_COLLECTION_NAME.keys())

selected_type = st.selectbox(
    "Select Category",
    options=available_collections,
    index=0 if available_collections else None
)

selected_collection = config.MONGODB_COLLECTION_NAME.get(selected_type)

# Add staff role filter if staff collection is selected
selected_role = None
if selected_collection and "staff" in selected_collection.lower():
    staff_roles = ["All"] + config.MONGODB_STAFF_ROLES
    selected_role = st.selectbox("Filter by role:", staff_roles)

# Analysis type
analysis_type = st.radio(
    "Analysis Type",
    ["Keyword-Based Analysis", "AI-Generated Thematic Analysis"],
    help="Choose between a faster keyword-based analysis or a more comprehensive AI-generated analysis"
)

# Keyword file selection for keyword-based analysis
keyword_file = None
if analysis_type == "Keyword-Based Analysis":
    keyword_type = selected_type
    keyword_file = "data/keywords.json" if keyword_type == "Student" else "data/staff_keywords.json"

    # Show sample of keywords
    with st.expander("Preview Selected Keywords"):
        keywords = load_keyword_data(keyword_file)
        if keywords:
            for category, terms in keywords.items():
                st.write(f"**{category}:** {', '.join(terms[:5])}{'...' if len(terms) > 5 else ''}")
        else:
            st.warning(f"No keywords found in {keyword_file}")

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
                            # Perform keyword-based analysis with file path
                            theme_data = identify_themes_with_keywords(
                                documents, file_path=keyword_file)
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
                            # Determine user type based on selected collection
                            user_type = "staff" if "staff" in selected_collection.lower() else "students"
                            
                            # Generate AI thematic analysis
                            ai_analysis = generate_ai_thematic_analysis(
                                documents, user_type=user_type)

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
- Follows a structured approach with theme identification, descriptions, and examples

""")
