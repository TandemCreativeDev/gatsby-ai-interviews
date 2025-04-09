import os
import sys
import json
import copy
from openai import OpenAI
from bson import ObjectId
from datetime import datetime

import streamlit as st

# Custom JSON encoder to handle MongoDB ObjectId and datetime
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import login functionality from the centralised login module
from login import setup_admin_page

# Initialize the admin page with login
if not setup_admin_page("Summarise Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("Generate a summarised overview of all transcripts in a collection.")

st.header("Transcript Collection Summary")

# Import after page header setup to ensure proper error handling
import config
from database import get_database, test_connection

# Function to generate a meta-summary from interviews
def generate_meta_summary(interviews):
    """
    Takes a list of interview documents (with transcripts removed)
    and generates a 100-word plain text summary using OpenAI.
    
    Args:
        interviews (list): List of interview documents
        
    Returns:
        str: 100-word plain text meta-summary
    """
    try:
        # Check if API key is available
        try:
            if "API_KEY_OPENAI" not in st.secrets:
                error_msg = "ERROR: API_KEY_OPENAI not found in secrets. OpenAI credentials are required."
                st.error(error_msg)
                raise ValueError(error_msg)
        except Exception as secrets_error:
            error_msg = f"Error accessing OpenAI credentials: {str(secrets_error)}"
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
                # If it's a staff interview, only keep the staff_analysis field if it exists
                if "staff_analysis" in interview_copy:
                    staff_only = {"staff_analysis": interview_copy["staff_analysis"]}
                    if "analyzed_at" in interview_copy:
                        staff_only["analyzed_at"] = interview_copy["analyzed_at"]
                    if "username" in interview_copy:
                        staff_only["username"] = interview_copy["username"]
                    cleaned_interviews.append(staff_only)
                else:
                    # Skip staff interviews without staff_analysis
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
            system_prompt = """You are an expert at analysing staff interview data about AI in education and creating incisive, insightful summaries.
            Your task is to create a 200-word plain text summary that captures the key patterns and insights across all staff respondents.
            Focus on the most prevalent themes regarding AI integration in education, notable patterns in the teaching approaches, and significant institutional considerations.
            Your summary should be in British English.
            """
            
            # Convert interview data to JSON format for the prompt using custom encoder
            interviews_json = json.dumps(cleaned_interviews, cls=MongoJSONEncoder)
            
            user_prompt = f"""
            Analyse the following collection of staff interview analyses about AI in education and create an incisive 200-word plain text summary 
            that captures the key patterns and insights across all staff respondents.
            
            Here are the staff interview analyses to summarise:
            
            {interviews_json}
            
            IMPORTANT INSTRUCTIONS:
            1. Create a plain text summary of approximately 200 words.
            2. Focus on key patterns, trends, and insights that emerge across multiple staff respondents.
            3. Highlight patterns related to educational settings, AI integration strategies, and implementation considerations.
            4. Emphasize notable agreements or differences in perspectives on adopting AI in educational contexts.
            5. Use British English spelling (e.g., "summarise" not "summarize").
            6. Do not structure the response as JSON or with headers - just plain text.
            """
        else:
            system_prompt = """You are an expert at analysing student interview data and creating incisive, insightful summaries.
            Your task is to create a 200-word plain text summary that captures the key patterns and insights across all student respondents.
            Focus on the most prevalent themes, notable patterns, and significant insights, especially those related to demographics like age and college.
            Your summary should be in British English.
            """
            
            # Convert interview data to JSON format for the prompt using custom encoder
            interviews_json = json.dumps(cleaned_interviews, cls=MongoJSONEncoder)
            
            user_prompt = f"""
            Analyse the following collection of student interview documents and create an incisive 200-word plain text summary 
            that captures the key patterns and insights across all respondents.
            
            Here are the interview documents to analyse:
            
            {interviews_json}
            
            IMPORTANT INSTRUCTIONS:
            1. Create a plain text summary of approximately 200 words.
            2. Focus on key patterns, trends, and insights that emerge across multiple student respondents.
            3. Specifically highlight any patterns related to demographics (age, college, gender) if present.
            4. Highlight any notable consensus or divergence in opinions.
            5. Use British English spelling (e.g., "summarise" not "summarize").
            6. Do not structure the response as JSON or with headers - just plain text.
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
        error_msg = "No collections found in the database. Please check your MongoDB connection."
        st.error(error_msg)
        raise ValueError(error_msg)
else:
    error_msg = "Could not connect to the database. Please check your MongoDB connection."
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
                    st.success(f"Successfully retrieved {len(documents)} interviews from the '{selected_collection}' collection.")
                else:
                    st.warning(f"No interviews found in the '{selected_collection}' collection.")
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
