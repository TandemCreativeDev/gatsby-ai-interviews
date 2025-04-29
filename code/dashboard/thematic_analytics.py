import streamlit as st
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter, defaultdict
from nltk.stem import WordNetLemmatizer
import pandas as pd
from openai import OpenAI

# Download necessary NLTK data (make sure to run this once)


def download_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')


def extract_user_prompts(transcript):
    """
    Extract only the user's prompts from the transcript

    Args:
        transcript (str): The full interview transcript

    Returns:
        list: List of the user's responses
    """
    if not transcript:
        return []

    # Extract lines starting with "user:"
    user_lines = []
    lines = transcript.split('\n')

    for line in lines:
        line = line.strip()
        if line.lower().startswith('user:'):
            # Extract content after "user:"
            content = line[5:].strip()
            if content:
                user_lines.append(content)

    return user_lines


def preprocess_text(text_list):
    """
    Preprocess text for thematic analysis

    Args:
        text_list (list): List of text strings

    Returns:
        list: List of preprocessed tokens
    """
    # Download necessary NLTK data
    download_nltk_data()

    # Initialize lemmatiser
    lemmatiser = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))

    # Additional stopwords relevant to our context
    additional_stopwords = {
        'ai', 'like', 'just', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
        'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself',
        'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
        'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs',
        'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these',
        'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
        'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but',
        'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with',
        'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after',
        'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over',
        'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
        'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 's', 't', 'can', 'will', 'don', "don't", 'should', "should've", 'now',
        'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn',
        "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn',
        "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't",
        'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn',
        "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn',
        "wouldn't", 'yeah', 'yes', 'using'
    }

    # Update stopwords
    stop_words.update(additional_stopwords)

    all_tokens = []

    for text in text_list:
        # Tokenize
        tokens = word_tokenize(text.lower())

        # Remove stopwords and non-alphabetic tokens
        filtered_tokens = [
            lemmatiser.lemmatize(token)
            for token in tokens
            if token.isalpha() and token not in stop_words and len(token) > 2
        ]

        all_tokens.extend(filtered_tokens)

    return all_tokens


def extract_key_terms(tokens, top_n=50):
    """
    Extract key terms from preprocessed tokens

    Args:
        tokens (list): List of preprocessed tokens
        top_n (int): Number of top terms to extract

    Returns:
        list: List of (term, count) tuples
    """
    # Count terms
    term_counts = Counter(tokens)

    # Get top terms
    top_terms = term_counts.most_common(top_n)

    return top_terms


def identify_themes_with_keywords(interviews):
    """
    Identify themes using predefined keywords

    Args:
        interviews (list): List of interview documents

    Returns:
        dict: Dictionary of themes and their frequency
    """
    # Define themes and their associated keywords
    theme_keywords = {
        "Time Efficiency": ["time", "quick", "fast", "efficient", "speed", "save", "productivity"],
        "Learning Support": ["understand", "explain", "concept", "clarify", "learn", "grasp", "comprehend"],
        "Creative Applications": ["create", "design", "generate", "creative", "art", "music", "write"],
        "Accuracy Concerns": ["wrong", "incorrect", "error", "mistake", "accurate", "reliable", "false"],
        "Ethical Considerations": ["ethics", "moral", "privacy", "fair", "bias", "right", "wrong"],
        "Future Employment": ["job", "career", "employ", "skill", "workplace", "future", "profession"],
        "Access & Equity": ["access", "equity", "equal", "privilege", "disadvantage", "barrier", "fair"],
        "Technical Skills": ["code", "program", "develop", "software", "technical", "algorithm", "data"],
        "Critical Thinking": ["critical", "think", "evaluate", "analyze", "assess", "judgment", "question"]
    }

    # Initialize theme counter
    theme_counts = {theme: 0 for theme in theme_keywords}
    theme_examples = {theme: [] for theme in theme_keywords}

    # Process each interview
    for interview in interviews:
        transcript = interview.get("transcript", "")
        user_responses = extract_user_prompts(transcript)

        # Process each response
        for response in user_responses:
            response_lower = response.lower()

            # Check for themes
            for theme, keywords in theme_keywords.items():
                # Check if any keyword appears in the response
                for keyword in keywords:
                    if f" {keyword}" in f" {response_lower} ":
                        theme_counts[theme] += 1
                        # Store a short example (first 100 chars)
                        example = response[:100] + \
                            "..." if len(response) > 100 else response
                        if example not in theme_examples[theme]:
                            theme_examples[theme].append(example)
                        break

    # Calculate percentages
    total_interviews = len(interviews)
    theme_percentages = {
        theme: round((count / total_interviews) * 100)
        for theme, count in theme_counts.items()
    }

    # Sort themes by frequency
    sorted_themes = sorted(
        theme_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "theme_counts": theme_counts,
        "theme_percentages": theme_percentages,
        "sorted_themes": sorted_themes,
        "theme_examples": theme_examples,
        "total_interviews": total_interviews
    }


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
        7. Avoid making claims about specific percentages - instead use words like "frequently", "commonly", "occasionally", "rarely" to express relative frequency
        8. Ensure all themes are grounded directly in the data, not inferred or assumed
        
        After the table, provide a brief interpretative commentary on each theme (1-2 paragraphs per theme) that explores the implications for education.
        
        Conclude with a short section titled "Implications for research" that identifies 2-3 key points about how this analysis could inform future research or education policy."""

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
        import datetime
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


def format_keyword_themes(theme_data):
    """
    Format keyword-based themes as markdown

    Args:
        theme_data (dict): Theme data from identify_themes_with_keywords

    Returns:
        str: Markdown formatted theme report
    """
    # Helper function to get percentage range
    def get_percentage_range(percentage):
        if percentage < 15:
            return "under 15%"
        elif percentage <= 30:
            return "15-30%"
        elif percentage <= 70:
            return "30-70%"
        elif percentage <= 85:
            return "71-85%"
        else:
            return "over 85%"

    markdown = "## Keyword-Based Thematic Analysis\n\n"
    markdown += f"Analysis based on {theme_data['total_interviews']} student interviews\n\n"

    markdown += "| Theme | Frequency | Percentage Range |\n"
    markdown += "|-------|-----------|------------------|\n"

    for theme, count in theme_data['sorted_themes']:
        if count > 0:
            percentage = theme_data['theme_percentages'][theme]
            range_text = get_percentage_range(percentage)
            markdown += f"| {theme} | {count}/{theme_data['total_interviews']} | {range_text} |\n"

    markdown += "\n### Theme Examples\n\n"

    for theme, examples in theme_data['theme_examples'].items():
        if examples:
            markdown += f"#### {theme}\n"
            # Show up to 3 examples per theme
            for i, example in enumerate(examples[:3]):
                markdown += f"{i+1}. \"{example}\"\n"
            markdown += "\n"

    return markdown
