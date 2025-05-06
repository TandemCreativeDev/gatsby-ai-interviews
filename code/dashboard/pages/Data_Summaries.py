from student_data_summary import (
    generate_consistent_meta_summary,
    calculate_demographic_stats,
    analyse_themes
)
from login import setup_admin_page
from database import get_database
import config
import sys
import os
import streamlit as st

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralised login module

# Import our new consistent summary functions

# Import data normalisation class

# Initialize the admin page with login
if not setup_admin_page("Consistent Summarise Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("Generate a consistent summary of transcripts in a collection.")

st.header("Transcript Collection Summary")

collection_options = config.MONGODB_COLLECTION_NAME.values()

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

# Options for data processing
with st.expander("Data Processing Options"):
    # Normalisation options
    use_normalisation = st.checkbox("Normalise categorical data", value=True,
                                    help="Standardize entries like college names, subjects, etc.")

    show_normalisation_details = st.checkbox("Show normalisation details", value=False,
                                             help="Display how data was normalised")

    # Display options
    show_raw_stats = st.checkbox("Show raw statistics (for verification)", value=False,
                                 help="Display the underlying counts before formatting")

# Process button to retrieve the interviews
if st.button("Retrieve Interviews"):
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
                    # Store the full documents in session state
                    st.session_state['interviews'] = documents

                    # Display count of retrieved documents with role info if applicable
                    role_info = ""
                    if "staff" in selected_collection.lower() and selected_role and selected_role != "All":
                        role_info = f" with role '{selected_role}'"

                    st.success(
                        f"Successfully retrieved {len(documents)} interviews{role_info} "
                        f"from the '{selected_collection}' collection.")
                else:
                    st.warning(
                        f"No interviews found in the "
                        f"'{selected_collection}' collection.")
    else:
        st.error("Please select a collection to retrieve interviews from.")

# Button to generate summary - only show if interviews have been retrieved
if 'interviews' in st.session_state and st.button("Generate Consistent Summary"):
    with st.spinner("Generating consistent summary from all interviews..."):
        interviews = st.session_state['interviews']

        # Display raw statistics if requested
        if show_raw_stats:
            st.subheader("Raw Statistics (For Verification)")

            # Calculate demographic statistics without normalisation
            demographic_stats, _ = calculate_demographic_stats(
                interviews, normalise=False)
            st.write("Demographics (without normalisation):")
            st.json(demographic_stats)

            # Calculate theme statistics
            theme_stats = analyse_themes(interviews)
            st.write("Themes:")
            st.json(theme_stats)

            st.divider()

        # Generate meta-summary using consistent processing method
        meta_summary, normalisation_info, docs_to_update = generate_consistent_meta_summary(
            interviews,
            normalise=use_normalisation,
            show_normalisation=show_normalisation_details
        )

        # Store summary in session state
        st.session_state['meta_summary'] = meta_summary
        st.session_state['docs_to_update'] = docs_to_update

        # Store normalisation info in session state
        if use_normalisation:
            st.session_state['normalisation_info'] = normalisation_info

        # Determine collection type for display
        if "staff" in selected_collection.lower():
            # Include role in the header if filtered
            role_info = ""
            if selected_role and selected_role != "All":
                role_info = f" ({selected_role})"

            st.subheader(f"Data Summary of Staff Interviews{role_info}")
            file_prefix = "staff"

            # Include role in the filename if filtered
            if selected_role and selected_role != "All":
                file_prefix = f"staff_{selected_role.lower()}"
        else:
            st.subheader("Data Summary of Student Interviews")
            file_prefix = "student"

        # Display the summary
        st.markdown(meta_summary)

        # Add download button for the summary
        st.download_button(
            label="Download Summary",
            data=meta_summary,
            file_name=f"{file_prefix}_data_summary.md",
            mime="text/markdown"
        )

        # Display normalisation details if requested
        if use_normalisation and show_normalisation_details and 'normalisation_info' in st.session_state:
            st.sidebar.subheader("Normalisation Details")

            # Show college normalisation
            if 'college_clusters' in normalisation_info:
                with st.sidebar.expander("College Name Normalisation"):
                    college_clusters = normalisation_info['college_clusters']
                    for canonical, variations in college_clusters.items():
                        if len(variations) > 1:  # Only show if multiple variations exist
                            st.sidebar.write(
                                f"**{canonical}** ({len(variations)} variations):")
                            for variation in variations:
                                st.sidebar.write(f"- {variation}")

            # Show subject normalisation
            if 'subject_clusters' in normalisation_info:
                with st.sidebar.expander("Subject Normalisation"):
                    subject_clusters = normalisation_info['subject_clusters']
                    for canonical, variations in subject_clusters.items():
                        if len(variations) > 1:  # Only show if multiple variations exist
                            st.sidebar.write(
                                f"**{canonical}** ({len(variations)} variations):")
                            for variation in variations:
                                st.sidebar.write(f"- {variation}")

        # Add explanation of normalised data
        if use_normalisation:
            print(docs_to_update[0:3])
            st.info("""
            ℹ️ **Note on Data Normalisation**

            This summary uses data normalisation to group similar entries together (e.g., "Fareham College" and "fareham college").
            This improves accuracy by handling variations in spelling, capitalization, and formatting.
            """)

            if not show_normalisation_details:
                st.write(
                    "Enable 'Show normalisation details' in the options to see how data was normalised.")

        # Add button to update the database with normalised data
        if use_normalisation and docs_to_update:
            st.divider()
            st.subheader("Update Database with Normalised Data")

            # Preview the data to be updated
            with st.expander(f"Preview Updates ({len(docs_to_update)} documents)"):

                st.write(f"**Number of documents to update:** {len(docs_to_update)}")

                # Show documents with most course types
                st.subheader("Documents with most course types")
                course_sorted_docs = sorted(docs_to_update, key=lambda x: len(x.get("course_types", [])), reverse=True)

                for i, doc in enumerate(course_sorted_docs[:5]):
                    num_course_types = len(doc.get("course_types", []))
                    st.write(f"**Document {i+1} ({num_course_types} course types):**")
                    st.json({k: v for k, v in doc.items() if k != "id"})

                # Show documents with most subjects
                st.subheader("Documents with most subjects")
                subject_sorted_docs = sorted(docs_to_update, key=lambda x: len(x.get("subjects", [])), reverse=True)

                for i, doc in enumerate(subject_sorted_docs[:5]):
                    num_subjects = len(doc.get("subjects", []))
                    st.write(f"**Document {i+1} ({num_subjects} subjects):**")
                    st.json({k: v for k, v in doc.items() if k != "id"})

            # Determine collection type
            collection_type = "Staff" if "staff" in selected_collection.lower() else "Student"
            print(collection_type)

            # Initialize update state tracking variables
            if 'update_started' not in st.session_state:
                st.session_state.update_started = False
            
            if 'update_completed' not in st.session_state:
                st.session_state.update_completed = False
                
            if 'update_results' not in st.session_state:
                st.session_state.update_results = None
                
            # Store collection type and documents for use across reruns
            if 'selected_collection_type' not in st.session_state:
                st.session_state.selected_collection_type = collection_type
                
            if 'docs_to_update_processed' not in st.session_state:
                # Process documents once and store in session state
                simple_docs = []
                for doc in docs_to_update:
                    simple_doc = {
                        "username": doc.get("username"),
                        "college": doc.get("college"),
                        "gender": doc.get("gender"),
                        "age_group": doc.get("age_group"),
                        "subjects": doc.get("subjects", []),
                        "course_types": doc.get("course_types", [])
                    }
                    simple_docs.append(simple_doc)
                st.session_state.docs_to_update_processed = simple_docs
            
            # Add button to update - disabled if update is in progress
            update_button_key = f"update_docs_button_{collection_type}"
            start_update = st.button(
                f"Update {len(docs_to_update)} documents with normalised data", 
                key=update_button_key,
                disabled=st.session_state.update_started
            )
            
            # Handle button click to start update
            if start_update:
                st.session_state.update_started = True
                st.session_state.update_completed = False
                st.rerun()  # Force rerun to show spinner
                
            # If update is started but not completed, do the update
            if st.session_state.update_started and not st.session_state.update_completed:
                with st.spinner(f"Updating {len(docs_to_update)} documents in database..."):
                    try:
                        from database import update_documents_with_normalised_data
                        
                        # Get the processed documents from session state
                        safe_docs = st.session_state.docs_to_update_processed
                        
                        # Log update start 
                        st.write(f"Starting update of {len(safe_docs)} documents...")
                        
                        # Call the update function with a very small batch size
                        updated_count, error_msg = update_documents_with_normalised_data(
                            safe_docs, st.session_state.selected_collection_type
                        )
                        
                        # Store results
                        st.session_state.update_results = {
                            'count': updated_count,
                            'error': error_msg
                        }
                        
                    except Exception as e:
                        # Catch any errors during update
                        st.session_state.update_results = {
                            'count': 0,
                            'error': f"Update failed with error: {str(e)}"
                        }
                    
                    # Mark update as completed
                    st.session_state.update_completed = True
                    st.session_state.update_started = False
                    st.rerun()  # Force rerun to display results
            
            # Display update results if available
            if st.session_state.update_completed and st.session_state.update_results:
                result = st.session_state.update_results
                if result.get('error'):
                    st.error(f"Error updating documents: {result['error']}")
                else:
                    if result.get('count', 0) > 0:
                        st.success(f"Successfully updated {result['count']} documents with normalised data")
                    else:
                        st.warning("No documents were updated")
                
                # Add option to reset and try again
                if st.button("Reset Update State", key="reset_update"):
                    # Clear update state
                    st.session_state.update_started = False
                    st.session_state.update_completed = False
                    st.session_state.update_results = None
                    st.session_state.pop('docs_to_update_processed', None)
                    st.rerun()

        # Store summary in session state
        st.session_state['meta_summary'] = meta_summary

# Add quick links to other summary types for comparison
st.sidebar.header("Summary Options")
st.sidebar.write("Navigate between different summary types:")

if st.sidebar.button("Go to AI-generated Summary"):
    js = f"""
    <script>
    window.parent.open('/Summarise_Transcripts', '_self');
    </script>
    """
    st.components.v1.html(js)

# Add explanatory information about the consistent summary
st.sidebar.markdown("""
### About Consistent Summary

This page provides a summary with:
- Consistent counting methodology
- Fixed demographic calculations
- Standardized percentage ranges
- Direct data extraction without AI interpretation

Use this for more reliable numerical reporting across multiple summary generations.
""")
