import nltk
import json
import os
import re


def download_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')


def load_keyword_data(file_path):
    """Load keyword categories from JSON file"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            print(f"Warning: Keywords file not found: {file_path}")
            return {}
    except Exception as e:
        print(f"Error loading keywords file: {e}")
        return {}


def extract_user_prompts(transcript):
    """
    Extract user/staff responses from interview transcripts in various formats

    Args:
        transcript (str): The full interview transcript

    Returns:
        list: List of the user's/staff's responses
    """
    if not transcript:
        return []

    # Extract all content based on various transcript formats
    user_lines = []
    lines = transcript.split('\n')

    # Format patterns to check:
    # 1. Standard prefixes (user:, staff:, teacher:, principal:)
    # 2. Chat format ("You said:", "Human:", etc.)
    # 3. Blank line after identifier (e.g., "ChatGPT said:" followed by content on next line)

    prefixes = [
        "user:", "staff:", "teacher:", "principal:",  # Standard format
        "you said:", "human:", "student:", "respondent:"  # Chat format
    ]

    # Track if we're in a user section (after an identifier)
    in_user_section = False
    current_user_text = ""

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:  # Skip empty lines
            continue

        line_lower = line.lower()

        # Check for prefixes that indicate user input
        is_user_input = False
        matched_prefix = None

        for prefix in prefixes:
            if line_lower.startswith(prefix):
                is_user_input = True
                matched_prefix = prefix
                break

        # Also check for "You said:" pattern
        if line_lower == "you said:" or re.match(r"^you\s+said\s*:$", line_lower):
            is_user_input = True
            matched_prefix = line
            in_user_section = True
            continue  # Content will be on next line

        # If we found a user input line
        if is_user_input and matched_prefix:
            # Extract content after the prefix
            content = line[len(matched_prefix):].strip()
            if content:
                user_lines.append(content)
            in_user_section = False  # Reset flag as we've processed this line

        # If we're in a user section from a previous line
        elif in_user_section:
            # Check if this line ends the user section (next identifier)
            if any(line_lower.startswith(p) for p in ["chatgpt said:", "claude said:", "assistant:", "interviewer:"]):
                # End of user section
                if current_user_text:
                    user_lines.append(current_user_text)
                current_user_text = ""
                in_user_section = False
            else:
                # Still in user section, add this line
                current_user_text += " " + line if current_user_text else line

    # Add any remaining user text
    if current_user_text:
        user_lines.append(current_user_text)

    # If we didn't find any user lines with the standard methods,
    # try a more aggressive approach to extract all non-system content
    if not user_lines:
        print("No user lines found with standard methods, trying alternative extraction...")
        # Look for any paragraph-like chunks
        paragraphs = []
        current_para = ""

        for line in lines:
            if line.strip():
                current_para += " " + line.strip() if current_para else line.strip()
            elif current_para:  # Empty line after content
                paragraphs.append(current_para)
                current_para = ""

        # Add the last paragraph if it exists
        if current_para:
            paragraphs.append(current_para)

        # Filter out likely system or interviewer lines
        for para in paragraphs:
            if not any(marker in para.lower() for marker in [
                "system:", "chatgpt:", "claude:", "assistant:", "interviewer:", "ai:", "model:"
            ]):
                user_lines.append(para)

    return user_lines


def identify_themes_with_keywords(interviews, theme_keywords=None, file_path=None):
    """
    Identify themes using predefined keywords

    Args:
        interviews (list): List of interview documents
        theme_keywords (dict, optional): Dictionary of themes and their keywords
        file_path (str, optional): Path to keywords JSON file

    Returns:
        dict: Dictionary of themes and their frequency
    """
    # Load keywords from file if not provided directly
    if theme_keywords is None:
        if file_path:
            theme_keywords = load_keyword_data(file_path)
        else:
            # Fallback to default file (student keywords)
            theme_keywords = load_keyword_data("data/keywords.json")

    # If still no keywords available, use empty dict
    if not theme_keywords:
        print("Warning: No themes/keywords available for analysis")
        return {"theme_counts": {}, "theme_percentages": {},
                "sorted_themes": [], "theme_examples": {}, "total_interviews": 0}

    # Initialize theme counter
    theme_counts = {theme: 0 for theme in theme_keywords}
    theme_examples = {theme: [] for theme in theme_keywords}

    # Process each interview
    interview_processed_count = 0
    for interview in interviews:
        interview_matched_themes = set()  # Track which themes were found in this interview

        transcript = interview.get("transcript", "")

        # Print a sample of the transcript for debugging
        is_staff = "staff" in file_path.lower() if file_path else False
        if is_staff:
            print(f"Staff transcript sample: {transcript[:200]}...")

        user_responses = extract_user_prompts(transcript)

        # Debug info for staff analysis
        if is_staff:
            print(f"Extracted {len(user_responses)} responses from staff transcript")
            if len(user_responses) > 0:
                print(f"First response sample: {user_responses[0][:100]}...")

        # Process each response
        for response in user_responses:
            response_lower = response.lower()

            # Check for themes
            for theme, keywords in theme_keywords.items():
                # Check if any keyword appears in the response
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    # Add spaces to match whole words
                    if f" {keyword_lower} " in f" {response_lower} " or \
                            response_lower.startswith(f"{keyword_lower} ") or \
                            response_lower.endswith(f" {keyword_lower}") or \
                            response_lower == keyword_lower:
                        if theme not in interview_matched_themes:
                            theme_counts[theme] += 1
                            interview_matched_themes.add(theme)
                        # Store a short example
                        example = response[:100] + "..." if len(response) > 100 else response
                        if example not in theme_examples[theme]:
                            theme_examples[theme].append(example)
                        break

        # Count this interview as processed regardless of whether themes were found
        interview_processed_count += 1

    # Calculate percentages
    total_interviews = interview_processed_count if interview_processed_count > 0 else len(interviews)
    theme_percentages = {
        theme: round((count / total_interviews) * 100) if total_interviews > 0 else 0
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


def format_keyword_themes(theme_data):
    """
    Format keyword-based themes as markdown

    Args:
        theme_data (dict): Theme data from identify_themes_with_keywords

    Returns:
        str: Markdown formatted theme report
    """

    markdown = "## Keyword-Based Thematic Analysis\n\n"
    markdown += f"Analysis based on {theme_data['total_interviews']} student interviews\n\n"

    markdown += "| Theme | Frequency | Percentage |\n"
    markdown += "|-------|-----------|------------|\n"

    for theme, count in theme_data['sorted_themes']:
        if count > 0:
            percentage = theme_data['theme_percentages'][theme]
            markdown += f"| {theme} | {count}/{theme_data['total_interviews']} | {percentage}% |\n"

    markdown += "\n### Theme Examples\n\n"

    for theme, examples in theme_data['theme_examples'].items():
        if examples:
            markdown += f"#### {theme}\n"
            # Show up to 3 examples per theme
            for i, example in enumerate(examples[:3]):
                markdown += f"{i+1}. \"{example}\"\n"
            markdown += "\n"

    return markdown
