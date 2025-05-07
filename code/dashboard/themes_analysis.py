import streamlit as st
import datetime
from openai import OpenAI
from keyword_analysis import extract_user_prompts


def generate_ai_thematic_analysis(interviews):
    """
    Generate a thematic analysis using OpenAI

    Args:
        interviews (list): List of interview documents

    Returns:
        str: AI-generated thematic analysis
    """
    try:
        # Check if API key is available
        if "API_KEY_OPENAI" not in st.secrets:
            return "Error: OpenAI API key not found in secrets. Please configure the OpenAI API key in Streamlit secrets."

        # Extract user prompts from transcripts
        all_prompts = []
        for interview in interviews:
            transcript = interview.get("transcript", "")
            user_responses = extract_user_prompts(transcript)
            all_prompts.extend(user_responses)

        # Limit number of responses if there are too many
        if len(all_prompts) > 100:
            # Take a representative sample
            st.info(
                f"Found {len(all_prompts)} responses. Selecting a representative sample of 100 for analysis.")
            sampling_interval = len(all_prompts) // 100
            sample_prompts = [all_prompts[i] for i in range(
                0, len(all_prompts), sampling_interval)][:100]
        else:
            sample_prompts = all_prompts

        # Combine responses with clear separators
        combined_responses = "\n\n---\n\n".join(sample_prompts)

        # If the combined text is too large, truncate it
        max_chars = 15000  # Adjust based on token limits
        if len(combined_responses) > max_chars:
            combined_responses = combined_responses[:max_chars] + \
                "\n\n[additional responses truncated due to length]"

        # Initialize OpenAI client
        client = OpenAI(api_key=st.secrets["API_KEY_OPENAI"])

        # Create the prompt for thematic analysis
        system_prompt = """
        You are an experienced educational researcher specialising in thematic analysis of 
        qualitative data. Your task is to analyse student responses about their experiences 
        with AI in education and identify key themes that emerge from the data.

        Your analysis should:
        1. Identify 5-7 major themes in the data
        2. For each theme, provide a clear description
        3. Include 3 verbatim quotation examples per theme
        4. Present the analysis in a table format with columns: 'Theme', 'Description of theme', and 'Example quotations'
        5. Use British English spelling (e.g., "summarise" not "summarize")
        6. Focus on patterns that appear across multiple responses
        7. Avoid making claims about specific percentages - instead use words like "frequently", "commonly", "occasionally", "rarely" to express relative
        frequency
        8. Ensure all themes are grounded directly in the data, not inferred or assumed

        After the table, provide a brief interpretative commentary on each theme (1-2 paragraphs per theme) that explores the implications for education.

        Conclude with a short section titled "Implications for research" that identifies 2-3 key points about how this analysis could inform future research or
        education policy."""

        user_prompt = f"""
        # Thematic Analysis Request

        ## Data
        Below are responses from students about their experiences with AI in education.
        Each response is separated by "---":

        ```
        {combined_responses}
        ```
        
        ## Task
        Please conduct a thematic analysis on these student responses following the guidelines in my system instructions.
        Focus on identifying patterns in how students perceive, use, and think about AI in educational contexts.
        
        ## Format Instructions
        1. Begin with a brief introduction about the purpose of the thematic analysis
        2. Present the themes table with columns: 'Theme', 'Description of theme', and 'Example quotations'
        3. Follow with interpretative commentary for each theme
        4. Conclude with "Implications for research" section
        5. Use markdown formatting throughout for readability
        """

        # Show progress message
        st.info(
            "Generating thematic analysis with OpenAI. This may take a few minutes...")

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4-turbo",  # Use the specified model or another suitable one
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Lower temperature for more consistent results
            max_tokens=4000
        )

        # Extract the generated thematic analysis
        thematic_analysis = response.choices[0].message.content

        # Add header and metadata
        timestamp = datetime.datetime.now().strftime("%d %B %Y, %H:%M")
        header = f"""# AI-Generated Thematic Analysis

Generated on: {timestamp}
Based on analysis of {len(interviews)} interviews containing {len(all_prompts)} student responses

"""

        return header + thematic_analysis

    except Exception as e:
        error_details = f"""
## Error Generating Thematic Analysis

Unfortunately, an error occurred while generating the thematic analysis:

```
{str(e)}
```

### Troubleshooting steps:

1. Verify that the OpenAI API key is correctly configured in Streamlit secrets
2. Check that the selected interviews contain valid transcript data
3. Try with a smaller sample of interviews (if you selected many)
4. Ensure you have a stable internet connection
        """
        return error_details
