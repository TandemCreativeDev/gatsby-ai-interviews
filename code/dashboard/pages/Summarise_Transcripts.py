from student_data_summary import generate_consistent_meta_summary
from login import setup_admin_page
from database import get_database, test_connection
import config
import copy
import json
import os
import sys
from datetime import datetime

import streamlit as st
from bson import ObjectId
from openai import OpenAI

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralised login module


# Custom JSON encoder to handle MongoDB ObjectId and datetime
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Initialize the admin page with login
if not setup_admin_page("Summarise Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("Generate a summarised overview of all transcripts in a collection.")

st.header("Transcript Collection Summary")

# Import after page header setup to ensure proper error handling


# Function to generate a meta-summary from interviews
def generate_meta_summary(interviews):
    """
    Takes a list of interview documents (with transcripts removed)
    and generates a 800-word plain text summary using OpenAI.

    Args:
        interviews (list): List of interview documents

    Returns:
        str: 800-word plain text meta-summary
    """
    try:
        # Check if API key is available
        try:
            if "API_KEY_OPENAI" not in st.secrets:
                error_msg = ("ERROR: API_KEY_OPENAI not found in secrets. "
                             "OpenAI credentials are required.")
                st.error(error_msg)
                raise ValueError(error_msg)
        except Exception as secrets_error:
            error_msg = ("Error accessing OpenAI credentials: "
                         f"{str(secrets_error)}")
            st.error(error_msg)
            raise ValueError(error_msg)

        # Initialize API client
        client = OpenAI(api_key=st.secrets["API_KEY_OPENAI"])

        # Create a deep copy and customize based on collection type
        cleaned_interviews = []
        for interview in interviews:
            interview_copy = copy.deepcopy(interview)

            if "transcript" in interview_copy:
                del interview_copy["transcript"]

            cleaned_interviews.append(interview_copy)
        print(f"Number of interviews being summarised: {len(interview_copy)}")
        interviews_json = json.dumps(
            cleaned_interviews, cls=MongoJSONEncoder
        )

        # Determine if we're summarizing staff or student interviews
        is_staff_collection = "staff" in selected_collection.lower()

        # Create the prompt for meta-summary based on collection type

        system_prompt = """
        You are an experienced educational researcher specialising in
        technology adoption in further education institutions. You have
        extensive experience analysing qualitative data from interviews
        and creating research summaries for policy reports and academic
        publications.
        Your expertise lies in identifying emerging patterns across diverse
        stakeholder perspectives and distilling complex findings into
        clear, actionable insights. You excel at balancing nuance with
        clarity and avoiding oversimplification while maintaining
        readability.
        Your summary should be in British English.
        """

        if is_staff_collection:
            user_prompt = f"""
            # FE Staff Summary
            ## Task
            Analyse the following collection of staff interview analyses about
            AI in education and create an incisive 800-word plain text summary
            that captures the key patterns and insights across all staff
            respondents.

            ## Details on Breakdown
            Your task is to create a 800-word plain text summary that captures
            perspectives of staff who are directly involved in teaching as
            well as those working in support functions like HR and estates.
            The summary should provide an overview of how AI is being used or
            could be used both in teaching and learning but also the running
            of the college.
            Focus on the most prevalent themes regarding AI integration in the
            college, notable patterns in the teaching approaches, and
            significant institutional considerations.
            Try to provide the information in three sections as follows:
                a. The current use of AI across the college
                    - Include examples/information on how AI is used in lesson
                    planning, delivery, or assessment.
                b. Where AI might add the most value in the future
                c. Issues around supporting better use of AI in the college
                    - Include examples/information on barriers respondents
                    foresee in integrating AI (e.g., staff training, ethical
                    concerns).

            ## Analysis JSON Summaries
            Here are the staff interview analyses to summarise:
            ```json
            {interviews_json}
            ```

            ## Criteria
            1. Create a plain text summary of approximately 800 words.
            2. Begin with a comprehensive demographic data table formatted in
            markdown (but not in a code block), showing:
                - College breakdown with counts and percentages
                - Staff role breakdown with counts and percentages
                - Subjects taught (list with count)
                - Departments with counts and percentages
            3. Focus on key patterns, trends, and insights that emerge across
            multiple staff respondents.
            4. Include quantitative insights about common themes (provide
            approximate percentages in ranges: under 15%, 15-30%, 30-70%,
            71-85%, over 85%) for topics such as:
                - Using AI for teaching
                - Using AI for work
                - Using AI outside education
                - Attitudes towards AI in education
                - Concerns about AI
                - Other prominent themes that emerge
            5. Highlight patterns related to educational settings, AI
            integration strategies, and implementation considerations.
            6. Emphasise notable agreements or differences in perspectives on
            adopting AI in educational contexts.
            7. Use British English spelling (e.g., "summarise" not
            "summarize").
            8. Do not structure the response as JSON or with headers - just
            plain text.
            9. IMPORTANT: Anonymise all references to specific teachers,
            principals, or colleges in examples.
            10. Avoid duplicating the same examples or points in different
            sections.
            11. Analyse how participants interacted with the AI during their
            sessions (e.g., whether they challenged findings, asked for
            examples, refined questions, or requested concrete outputs).
            12. Ensure the summary can be filtered to produce separate
            summaries for different staff roles (principals, teachers, and
            support staff).
            13. Do not structure the response as JSON or with headers - just
            plain text after the initial table.
            14. Use markdown to format your response, if using paragraph
            headings make them level 4 headings.
            15. IMPORTANT: Do not fabricate any information, all findings must
            be explicitly in the interviews data, particularly demographic
            information. Circle back and double check your numbers against the
            interviews, recalculate if in doubt.
            """
        else:
            meta_summary, _, _ = generate_consistent_meta_summary(
                interviews
            )
            user_prompt = f"""
            # FE Student Summary

            ## Task
            Analyse the following collection of student interview documents
            and create an incisive 800-word plain text summary that captures
            the key patterns and insights across all respondents.

            ## Detail of Breakdown
            Your task is to create a 800-word plain text summary that captures
            the key patterns and insights across all student respondents.
            Focus on the most prevalent themes, notable patterns, and
            significant insights.

            ## Analysis JSON Summaries
            Here are the interview documents to analyse:
            ```json
            {interviews_json}
            ```

            ## Criteria
            1. Create a plain text summary of approximately 800 words.
            2. Focus on key patterns, trends, and insights that emerge across
            multiple student respondents.
            3. Include quantitative insights about common themes (provide
            approximate percentages in ranges: under 15%, 15-30%, 30-70%,
            71-85%, over 85%) based on the consistent data analysis listed below.
            Do not stray from the numbers contained there, these are definitive.
            Include this data at the top of your response, exactly how it is presented,
            including the tables.
            4. Present insights on how different demographic groups may have
            different perspectives or experiences.
            5. Highlight any notable consensus or divergence in opinions.
            6. Anonymise all references to specific students, teachers, or
            colleges in examples.
            7. Use British English spelling (e.g., "summarise" not
            "summarize").
            8. Try to provide the information in three sections as follows:
                a. Current use of AI by students
                    - Include examples of how AI is used for coursework,
                    research, or personal development
                b. Where students believe AI might add the most value in their
                education
                c. Issues and challenges students identify around AI in
                education
                    - Include examples of concerns or barriers students mention
            9. Do not structure the response as JSON or with headers - just
            plain text after the initial demographic table.
            10. Use markdown to format your response, if using paragraph
            headings make them level 4 headings.
            11. IMPORTANT: Do not fabricate any information, all findings must
            be explicitly in the interviews data, particularly demographic
            information. Circle back and double check your numbers against the
            interviews, recalculate if in doubt.

            ## Consistent Data Analysis
            {meta_summary}
            """

        # Call OpenAI to generate the meta-summary
        response = client.chat.completions.create(
            model=config.MODEL['analysis'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        # Extract the result

        result = response.choices[0].message.content
        return result

    except Exception as e:
        error_msg = f"Error generating meta-summary: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        # Raise the error instead of returning a fallback message
        st.error(error_msg)
        raise


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
if 'interviews' in st.session_state and st.button("Generate Summary"):
    with st.spinner("Generating summary from all interviews..."):
        interviews = st.session_state['interviews']

        # Generate meta-summary
        meta_summary = generate_meta_summary(interviews)

        # Store and display summary
        st.session_state['meta_summary'] = meta_summary

        # Determine collection type for display
        if "staff" in selected_collection.lower():
            # Include role in the header if filtered
            role_info = ""
            if selected_role and selected_role != "All":
                role_info = f" ({selected_role})"

            st.subheader(f"Summary of Staff Interviews{role_info}")
            file_prefix = "staff"

            # Include role in the filename if filtered
            if selected_role and selected_role != "All":
                file_prefix = f"staff_{selected_role.lower()}"
        else:
            st.subheader("Summary of Student Interviews")
            file_prefix = "student"

        st.write(meta_summary)

        # Add download button for the summary
        st.download_button(
            label="Download Summary",
            data=meta_summary,
            file_name=f"{file_prefix}_interview_summary.txt",
            mime="text/plain"
        )
