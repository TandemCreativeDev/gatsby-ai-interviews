import json
from openai import OpenAI
import streamlit as st
import os as os
import datetime

import config

# Load schemas


def load_schema(base_path, fallback_path, error_message):
    if os.path.exists(base_path):
        path_to_use = base_path
    elif os.path.exists(fallback_path):
        path_to_use = fallback_path
    else:
        raise FileNotFoundError(error_message)

    with open(path_to_use, "r") as f:
        return json.load(f)


student_schema = load_schema(
    "data/schema.json",
    "../data/schema.json",
    "Neither data/schema.json nor ../data/schema.json were found."
)

staff_schema = load_schema(
    "data/staff_schema.json",
    "../data/staff_schema.json",
    "Neither data/staff_schema.json nor ../data/staff_schema.json were found."
)


def generate_transcript_summary(transcript, type="Student"):
    """
    Takes a transcript and sends it to OpenAI's model to generate a summary
    according to the appropriate schema format.

    Args:
        transcript (str): The full transcript of the interview
        type (str): The type of transcript - "Student" or "Staff"

    Returns:
        dict: JSON response containing the summary in the schema format
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

        # Return mock data if needed
        if use_mock_data:
            print("Using mock data instead of calling API")
            if type == "Staff":
                mock_data = staff_schema.copy()
                mock_data["analyzed_at"] = datetime.datetime.now().isoformat()
                return mock_data
            else:
                return student_schema

        # Initialize API client
        client = OpenAI(api_key=st.secrets["API_KEY_OPENAI"])
        print("OpenAI client initialized successfully")

        # Set schema and prompts based on type
        if type == "Staff":
            schema_to_use = staff_schema
            system_prompt = """
            You are an expert at analysing staff interview transcripts about
            AI in further education, extracting key information according to a
            schema and anonymising sensitive personal data or confidential
            content.
            Return ONLY valid JSON without additional text. Follow the exact
            schema provided.
            IMPORTANT: If you cannot find information for a specific field in
            the transcript, simply remove those keys entirely, including the
            keys up the hierarchy if the whole category is empty. DO NOT use
            the example values from the schema as defaults.
            """
            user_prompt = f"""
            # FE Staff Analysis

            ## Task
            Analyse the following staff interview transcript and create a
            detailed summary using this exact JSON schema format, witholding
            only they keys that are not used:
            ```json
            {schema_to_use}
            ```

            ## Transcript
            Here is the transcript to analyse:
            {transcript}

            ## Criteria
            1. If you cannot find information for a specific field in the
            transcript, leave that field empty (empty string, empty array, or
            null as appropriate).
            2. DO NOT use the example values from the schema as defaults.
            3. Where the schema shows string arrays (indicated by ["string"]),
            include all relevant points mentioned in the transcript.
            4. Return ONLY the valid JSON object without any additional text,
            explanations, or commentary.
            5. For sentiment analysis, assess the overall tone and attitude
            toward AI integration in education.
            6. For 'teaching_and_learning', focus on "How AI is used in lesson
            planning, delivery, or assessment".
            7. For 'anticipated_challenges', focus on "What barriers the
            respondent foresees in integrating AI (e.g., staff training,
            ethical concerns)".
            8. When extracting information about proposed applications,
            consider separating them into administrative uses, teaching
            applications, and student-facing tools.
            9. When assessing sentiment, consider both specific concerns and
            perceived benefits of AI integration.
            10. Include information about staff training needs, data privacy
            concerns, and equity and inclusion considerations where mentioned.
            """
        else:
            schema_to_use = student_schema
            system_prompt = """
            You are an expert at analysing interview transcripts, extracting
            key information according to a schema and anonymising sensitive
            personal data or confidential and explicit content.
            Return ONLY valid JSON without additional text. Follow the exact
            schema provided.
            IMPORTANT: If you cannot find information for a specific field in
            the transcript, leave that field empty (empty string, empty array,
            or null as appropriate). DO NOT use the example values from the
            schema as defaults.
            """
            user_prompt = f"""
            # FE Student Analysis

            ## Task
            Analyse the following interview transcript and create a summary
            using this exact JSON schema format:

            ```json
            {schema_to_use}
            ```
            For the last key "transcript", you must redact personal data or
            sensitive, confidential or even explicit information that the user
            may inadvertently disclose from the transcript and return it with
            [redacted] in the place of the censored information. Be mindful
            not to redact information that does not fall into this category as
            the transcripts should remain readable.

            ## Transcript
            Here is the transcript to analyse:

            {transcript}

            ## Criteria
            1. If you cannot find information for a specific field in the
            transcript, leave that field empty (empty string, empty array, or
            null as appropriate).
            2. DO NOT use the example values from the schema as defaults.
            3. Return ONLY the valid JSON object without any additional text,
            explanations, or commentary.
            """

        # Call OpenAI API to generate the summary
        print(f"Calling OpenAI API with model: ${config.MODEL['analysis']}")
        response = client.chat.completions.create(
            model=config.MODEL['analysis'],
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        print("API call completed successfully")

        # Extract the JSON response
        result = response.choices[0].message.content
        print(f"Raw API Response: {result}")

        # Parse the response as JSON
        summary_json = json.loads(result)

        # Add timestamp for staff analysis
        summary_json["analysed_at"] = datetime.datetime.now().isoformat()

        # Print the summary to console for debugging
        print(f"{type} Transcript Analysis:")
        print(json.dumps(summary_json, indent=2))

        return summary_json

    except Exception as e:
        print(f"Error generating transcript analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "responses": {},
            "sentiment_analysis": {},
            "analysed_at": datetime.datetime.now().isoformat()
        }
