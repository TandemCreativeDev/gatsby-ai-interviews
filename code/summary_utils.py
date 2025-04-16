import json
from openai import OpenAI
import streamlit as st
import os as os
import datetime

import config

# Load student schema
schema_path = "data/schema.json"
fallback_path = "../data/schema.json"

if os.path.exists(schema_path):
    path_to_use = schema_path
elif os.path.exists(fallback_path):
    path_to_use = fallback_path
else:
    raise FileNotFoundError("Neither data/schema.json nor ../data/schema.json were found.")

with open(path_to_use, "r") as f:
    schema = json.load(f)

# Load staff schema
staff_schema_path = "data/staff_schema.json"
staff_fallback_path = "../data/staff_schema.json"

if os.path.exists(staff_schema_path):
    staff_path_to_use = staff_schema_path
elif os.path.exists(staff_fallback_path):
    staff_path_to_use = staff_fallback_path
else:
    raise FileNotFoundError("Neither data/staff_schema.json nor ../data/staff_schema.json were found.")

with open(staff_path_to_use, "r") as f:
    staff_schema = json.load(f)

def generate_transcript_summary(transcript, type="Student"):
    """
    Takes a transcript and sends it to OpenAI's o3-mini model to generate a summary
    according to the schema format.
    
    Args:
        transcript (str): The full transcript of the interview
        type (str): The type of transcript - "Student" or "Staff"
        
    Returns:
        dict: JSON response containing the summary in the schema format
    """
    if type == "Staff":
        return generate_staff_transcript_summary(transcript)
    else:
        return generate_student_transcript_summary(transcript)

def generate_student_transcript_summary(transcript):
    """
    Takes a student transcript and sends it to OpenAI's o3-mini model to generate a summary
    according to the student schema format.
    
    Args:
        transcript (str): The full transcript of the interview
        
    Returns:
        dict: JSON response containing the summary in the schema format
    """
    try:
        # Check if API key is available
        use_mock_data = False
        try:
            if "API_KEY_OPENAI" not in st.secrets:
                print("WARNING: API_KEY_OPENAI not found in secrets")
                # Look at what secrets are available (without printing the actual values)
                print(f"Available secrets: {list(st.secrets.keys())}")
                print("Using mock data for testing")
                use_mock_data = True
        except Exception as secrets_error:
            print(f"Error accessing secrets: {str(secrets_error)}")
            print("Using mock data for testing")
            use_mock_data = True
            
        if use_mock_data:
            # Return mock data for testing without API
            print("Using mock data instead of calling API")
            mock_summary = schema
            return mock_summary
            
        # Initialize API client
        client = OpenAI(api_key=st.secrets["API_KEY_OPENAI"])
        print(f"OpenAI client initialized successfully")
        
        # Create the prompt with instructions to summarize according to the schema
        system_prompt = """You are an expert at analysing interview transcripts, extracting key information according to a schema and anonymising sensitive personal data or confidential and explicit content.
        Return ONLY valid JSON without additional text. Follow the exact schema provided.
        IMPORTANT: If you cannot find information for a specific field in the transcript, leave that field empty (empty string, empty array, or null as appropriate). DO NOT use the example values from the schema as defaults."""
        
        user_prompt = f"""
        Analyse the following interview transcript and create a summary using this exact JSON schema format:
        
        ```json
        {schema}
        ```
        For the last key "transcript", you must redact personal data or sensitive, confidential or even explicit information that the user may inadvertently disclose from the transcript and return it with [redacted] in the place of the censored information. Be mindful not to redact information that does not fall into this category as the transcripts should remain readable.
        Here is the transcript to analyse:
        
        {transcript}
        
        IMPORTANT INSTRUCTIONS:
        1. If you cannot find information for a specific field in the transcript, leave that field empty (empty string, empty array, or null as appropriate).
        2. DO NOT use the example values from the schema as defaults.
        3. Return ONLY the valid JSON object without any additional text, explanations, or commentary.
        """
        
        # Call OpenAI o3-mini to generate the summary
        print(f"Calling OpenAI API with model: ${config.MODEL['analysis']}")
        response = client.chat.completions.create(
            model=config.MODEL['analysis'],
            # Temperature not supported for o3-mini model
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        print(f"API call completed successfully")
        
        # Extract the JSON response
        result = response.choices[0].message.content
        print(f"Raw API Response: {result}")
        
        # Parse the response as JSON
        summary_json = json.loads(result)
        
        # Print the summary to console for debugging
        print("Transcript Summary:")
        print(json.dumps(summary_json, indent=2))
        
        return summary_json
        
    except Exception as e:
        print(f"Error generating transcript summary: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return an empty structure in case of error
        return {
            "responses": {
                "about_user": {},
                "ai_in_learning": {},
                "ai_outside_learning": {},
                "ai_in_teaching": {},
                "concerns_about_ai": {},
                "future_with_ai": {},
                "ai_vs_past_generations": {}
            },
            "sentiment_analysis": {}
        }

def generate_staff_transcript_summary(transcript):
    """
    Takes a staff transcript and sends it to OpenAI's o3-mini model to generate a summary
    according to the staff schema format.
    
    Args:
        transcript (str): The full transcript of the interview
        
    Returns:
        dict: JSON response containing the summary and staff analysis
    """
    try:
        # Check if API key is available
        use_mock_data = False
        try:
            if "API_KEY_OPENAI" not in st.secrets:
                print("WARNING: API_KEY_OPENAI not found in secrets")
                print(f"Available secrets: {list(st.secrets.keys())}")
                print("Using mock data for testing")
                use_mock_data = True
        except Exception as secrets_error:
            print(f"Error accessing secrets: {str(secrets_error)}")
            print("Using mock data for testing")
            use_mock_data = True
            
        if use_mock_data:
            # Return mock data for testing without API
            print("Using mock data instead of calling API")
            # The staff_schema should already have the responses structure
            mock_data = staff_schema.copy()
            mock_data["analyzed_at"] = datetime.datetime.now().isoformat()
            return mock_data
            
        # Initialize API client
        client = OpenAI(api_key=st.secrets["API_KEY_OPENAI"])
        print(f"OpenAI client initialized successfully")
        
        # Create the prompt with instructions to summarize according to the staff schema
        system_prompt = """You are an expert at analysing staff interview transcripts about AI in further education, extracting key information according to a schema and anonymising sensitive personal data or confidential content.
        Return ONLY valid JSON without additional text. Follow the exact schema provided.
        IMPORTANT: If you cannot find information for a specific field in the transcript, leave that field empty (empty string, empty array, or null as appropriate). DO NOT use the example values from the schema as defaults."""
        
        user_prompt = f"""
        Analyse the following staff interview transcript and create a detailed summary using this exact JSON schema format:
        
        ```json
        {staff_schema}
        ```
        
        Here is the transcript to analyse:
        
        {transcript}
        
        IMPORTANT INSTRUCTIONS:
        1. If you cannot find information for a specific field in the transcript, leave that field empty (empty string, empty array, or null as appropriate).
        2. DO NOT use the example values from the schema as defaults.
        3. Where the schema shows string arrays (indicated by ["string"]), include all relevant points mentioned in the transcript.
        4. Return ONLY the valid JSON object without any additional text, explanations, or commentary.
        5. For sentiment analysis, assess the overall tone and attitude toward AI integration in education.
        """
        
        # Call OpenAI to generate the summary
        print(f"Calling OpenAI API with model: ${config.MODEL['analysis']}")
        response = client.chat.completions.create(
            model=config.MODEL['analysis'],
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        print(f"API call completed successfully")
        
        # Extract the JSON response
        result = response.choices[0].message.content
        print(f"Raw API Response: {result}")
        
        # Parse the response as JSON
        analysis_json = json.loads(result)
        
        # Just add the analyzed_at timestamp - analysis_json already has responses structure
        analysis_json["analyzed_at"] = datetime.datetime.now().isoformat()
        summary_json = analysis_json
        
        # Print the summary to console for debugging
        print("Staff Transcript Analysis:")
        print(json.dumps(summary_json, indent=2))
        
        return summary_json
        
    except Exception as e:
        print(f"Error generating staff transcript analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return an empty structure in case of error, with responses key
        return {
            "responses": {
                "educational_setting": {},
                "ai_integration_strategy": {},
                "teaching_and_learning": {},
                "stakeholder_perspectives": {},
                "implementation_considerations": {},
                "specialised_applications": {},
                "future_outlook": {}
            },
            "sentiment_analysis": {},
            "analyzed_at": datetime.datetime.now().isoformat()
        }
