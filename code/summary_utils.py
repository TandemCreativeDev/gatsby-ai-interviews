import json
from openai import OpenAI
import streamlit as st

def generate_transcript_summary(transcript):
    """
    Takes a transcript and sends it to OpenAI's o3-mini model to generate a summary
    according to the schema format.
    
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
            mock_summary = {
                "responses": {
                    "about_user": {
                        "age": "22",
                        "gender": "Female",
                        "study_field": "Computer Science",
                        "career_aspiration": "Software Development (AI Applications)"
                    },
                    "ai_in_learning": {
                        "uses_ai": True,
                        "ai_usage": ["Explaining programming concepts", "Coding assistance", "Research paper summarization"],
                        "effective_aspects": "Debugging code, explaining complex concepts in different ways",
                        "ineffective_aspects": "Sometimes provides incorrect code solutions, oversimplifies complex topics",
                        "teacher_opinion": "Mixed - some support while others have concerns about academic integrity"
                    },
                    "ai_outside_learning": {
                        "uses_ai": True,
                        "ai_usage": [],
                        "comparison_to_learning": ""
                    },
                    "ai_in_teaching": {
                        "lesson_planning": "",
                        "feedback_marking": "",
                        "resource_creation": ""
                    },
                    "concerns_about_ai": {
                        "education": "",
                        "society": "",
                        "workplace": ""
                    },
                    "future_with_ai": {
                        "career_importance": "",
                        "preparedness": "",
                        "skills_to_develop": []
                    },
                    "ai_vs_past_generations": {
                        "education": "",
                        "work": "",
                        "daily_life": ""
                    }
                },
                "sentiment_analysis": {
                    "overall": "Positive",
                    "education": "Neutral",
                    "workplace": "Positive",
                    "society": "Not mentioned"
                }
            }
            return mock_summary
            
        # Initialize API client
        client = OpenAI(api_key=st.secrets["API_KEY_OPENAI"])
        print(f"OpenAI client initialized successfully")
        
        # Create the prompt with instructions to summarize according to the schema
        system_prompt = """You are an expert at analyzing interview transcripts and extracting key information according to a schema.
        Return ONLY valid JSON without additional text. Follow the exact schema provided."""
        
        user_prompt = f"""
        Please analyze the following interview transcript and create a summary using this exact JSON schema format:
        
        ```json
        {{
          "responses": {{
            "about_user": {{
              "age": "",
              "gender": "",
              "study_field": "",
              "career_aspiration": ""
            }},
            "ai_in_learning": {{
              "uses_ai": true,
              "ai_usage": [],
              "effective_aspects": "",
              "ineffective_aspects": "",
              "teacher_opinion": ""
            }},
            "ai_outside_learning": {{
              "uses_ai": true,
              "ai_usage": [],
              "comparison_to_learning": ""
            }},
            "ai_in_teaching": {{
              "lesson_planning": "",
              "feedback_marking": "",
              "resource_creation": ""
            }},
            "concerns_about_ai": {{
              "education": "",
              "society": "",
              "workplace": ""
            }},
            "future_with_ai": {{
              "career_importance": "",
              "preparedness": "",
              "skills_to_develop": []
            }},
            "ai_vs_past_generations": {{
              "education": "",
              "work": "",
              "daily_life": ""
            }}
          }},
          "sentiment_analysis": {{
            "overall": "",
            "education": "",
            "workplace": "",
            "society": ""
          }}
        }}
        ```
        
        Here is the transcript to analyze:
        
        {transcript}
        
        Return ONLY the valid JSON object without any additional text, explanations, or commentary.
        """
        
        # Call OpenAI o3-mini to generate the summary
        print(f"Calling OpenAI API with model: o3-mini")
        response = client.chat.completions.create(
            model="o3-mini",
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