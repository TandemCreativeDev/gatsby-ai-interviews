import nltk


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
