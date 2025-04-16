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
from login import setup_admin_page


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

            # For staff interviews (based on selected collection name)
            if "staff" in selected_collection.lower():
                # Check if staff interview has responses
                if "responses" in interview_copy:
                    # Remove the transcript to save tokens,
                    # but keep all other metadata
                    if "transcript" in interview_copy:
                        del interview_copy["transcript"]
                    cleaned_interviews.append(interview_copy)
                else:
                    # Skip staff interviews without responses
                    continue
            else:
                # For student interviews, remove the transcript to save tokens
                if "transcript" in interview_copy:
                    del interview_copy["transcript"]
                cleaned_interviews.append(interview_copy)

        # Determine if we're summarizing staff or student interviews
        is_staff_collection = "staff" in selected_collection.lower()

        # Create the prompt for meta-summary based on collection type
        if is_staff_collection:
            system_prompt = """
            You are an expert at analysing staff interview
             data about AI in further education and creating incisive, insightful
             summaries.
            Your task is to create a 800-word plain text summary that captures
             perspectives of staff who are directly involved in teaching as well
             as those working in support functions like HR and estates. The summary
             should provide an overview of how AI is being used or could be used
             both in teaching and learning but also the running of the college.
            Focus on the most prevalent themes regarding AI integration in
             the college, notable patterns in the teaching approaches, and
             significant institutional considerations.
            Start each summary with a table providing information about the
             respondents such as subjects taught or department.
            Try to provide the information in three sections as follows:
                a. The current use of AI across the college
                b. Where AI might add the most value in the future
                c. Issues around supporting better use of AI in the college.
            Your summary should be in British English.
            """

            # Convert interview data to JSON format
            # for the prompt using custom encoder
            interviews_json = json.dumps(
                cleaned_interviews, cls=MongoJSONEncoder)

            user_prompt = f"""
            Analyse the following collection of staff interview analyses about
             AI in education and create an incisive 800-word plain text summary
            that captures the key patterns and insights across all staff
             respondents.

            Here are the staff interview analyses to summarise:

            {interviews_json}

            IMPORTANT INSTRUCTIONS:
            1. Create a plain text summary of approximately 800 words.
            2. Focus on key patterns, trends, and insights that emerge across
             multiple staff respondents.
            3. Include demographic breakdowns where available (age, gender,
             subjects taught).
            4. Highlight patterns related to educational settings, AI
             integration strategies, and implementation considerations.
            5. Emphasize notable agreements or differences in perspectives on
             adopting AI in educational contexts.
            6. Use British English spelling (e.g., "summarise" not
             "summarize").
            7. Do not structure the response as JSON or with headers - just
             plain text.
            """
        else:
            system_prompt = """You are an expert at analysing student
             interview data and creating incisive, insightful summaries.
            Your task is to create a 800-word plain text summary that captures
             the key patterns and insights across all student respondents.
            Focus on the most prevalent themes, notable patterns, and
             significant insights.
            Include detailed breakdowns of participant responses based on
             demographics like age, gender, and college where that information
             is available. Your summary should be in British English.
            """

            # Convert interview data to JSON format
            # for the prompt using custom encoder
            interviews_json = json.dumps(
                cleaned_interviews, cls=MongoJSONEncoder)

            user_prompt = f"""
            Analyse the following collection of student interview documents
             and create an incisive 800-word plain text summary that captures
             the key patterns and insights across all respondents.

            Here are the interview documents to analyse:

            {interviews_json}

            IMPORTANT INSTRUCTIONS:
            1. Create a plain text summary of approximately 800 words.
            2. Focus on key patterns, trends, and insights that emerge across
             multiple student respondents.
            3. Include detailed demographic breakdowns of responses based on
             age, college, and gender where available.
            4. Present insights on how different demographic groups may have
             different perspectives or experiences.
            5. Highlight any notable consensus or divergence in opinions.
            6. Use British English spelling (e.g., "summarise" not
             "summarize").
            7. Do not structure the response as JSON or with headers - just
             plain text.
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

# Process button to retrieve the interviews
if st.button("Retrieve Interviews"):
    if selected_collection:
        with st.spinner("Retrieving interviews..."):
            # Get the database
            db = get_database()
            if db is not None:
                # Access the collection directly
                collection = db[selected_collection]

                # Query all documents
                documents = list(collection.find({}))

                if documents:
                    # Store the full documents in session state
                    st.session_state['interviews'] = documents

                    # Display count of retrieved documents
                    st.success(
                        f"Successfully retrieved {len(documents)} interviews "
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
            st.subheader("Summary of Staff Interviews")
            file_prefix = "staff"
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
