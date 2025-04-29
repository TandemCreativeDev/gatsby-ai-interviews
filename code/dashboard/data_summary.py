import streamlit as st
import pandas as pd
from database import get_database
import json
from datetime import datetime
import re
from data_normaliser import DataNormaliser


def calculate_demographic_stats(interviews, normalise=True):
    """
    Calculate demographic statistics from interview documents
    This processes the raw data without relying on AI to ensure consistency

    Args:
        interviews (list): List of interview documents from MongoDB
        normalise (bool): Whether to normalise categorical values

    Returns:
        dict: Demographics statistics and normalisation info if requested
    """
    if normalise:
        # Use DataNormaliser to normalise all categorical values
        normaliser = DataNormaliser()
        stats = normaliser.generate_stats_with_normalised_values(interviews)

        # Return normalisation details for UI display
        _, _, college_clusters = normaliser.normalise_field_values(
            interviews, "college", "college")

        # Extract and normalise subjects
        subjects = []
        for doc in interviews:
            if ("responses" in doc and
                "about_user" in doc["responses"] and
                    "study_field" in doc["responses"]["about_user"]):
                subject = doc["responses"]["about_user"].get("study_field")
                if subject:
                    subjects.append(subject)

        _, subject_clusters = normaliser.cluster_similar_values(
            subjects, "subject")

        normalisation_info = {
            "college_clusters": college_clusters,
            "subject_clusters": subject_clusters
        }

        return stats, normalisation_info
    else:
        # Original implementation for non-normalised statistics
        # Initialize counters
        stats = {
            "gender": {},
            "college": {},
            "age_group": {},
            "subjects": {},
            "course_types": {}
        }

        # Course type patterns for regex detection
        course_patterns = {
            "A-levels": r'\b[aA][\s-]levels?\b|\b[aA] level\b',
            "BTECs": r'\bbtecs?\b|\bBTECs?\b',
            "Apprenticeships": r'\bapprenticeships?\b|\bApprenticeships?\b',
            "T-levels": r'\b[tT][\s-]levels?\b|\b[tT] level\b'
        }

        # Process each interview
        for interview in interviews:
            # Gender counts
            gender = interview.get("gender", "Unknown")
            if gender:
                stats["gender"][gender] = stats["gender"].get(gender, 0) + 1
            else:
                stats["gender"]["Unknown"] = stats["gender"].get(
                    "Unknown", 0) + 1

            # College counts
            college = interview.get("college", "Unknown")
            if college:
                stats["college"][college] = stats["college"].get(
                    college, 0) + 1
            else:
                stats["college"]["Unknown"] = stats["college"].get(
                    "Unknown", 0) + 1

            # Age group counts
            age_group = interview.get("age_group", "Unknown")
            if age_group:
                stats["age_group"][age_group] = stats["age_group"].get(
                    age_group, 0) + 1
            else:
                stats["age_group"]["Unknown"] = stats["age_group"].get(
                    "Unknown", 0) + 1

            # Extract subjects from responses
            if "responses" in interview and "about_user" in interview["responses"]:
                study_field = interview["responses"]["about_user"].get(
                    "study_field")
                if study_field:
                    stats["subjects"][study_field] = stats["subjects"].get(
                        study_field, 0) + 1

            # Extract course types from transcript using regex
            transcript = interview.get("transcript", "")
            if transcript:
                for course_type, pattern in course_patterns.items():
                    if re.search(pattern, transcript):
                        stats["course_types"][course_type] = stats["course_types"].get(
                            course_type, 0) + 1

        return stats, {}


def analyze_themes(interviews):
    """
    Analyze themes from interview documents
    This processes the raw data without relying on AI to ensure consistency

    Args:
        interviews (list): List of interview documents from MongoDB

    Returns:
        dict: Theme statistics
    """
    # Initialize theme counters
    themes = {
        "ai_for_learning": {"count": 0, "total": 0},
        "ai_for_assignments": {"count": 0, "total": 0},
        "ai_outside_learning": {"count": 0, "total": 0},
        "attitudes": {"positive": 0, "neutral": 0, "negative": 0, "total": 0},
        "concerns_about_ai": {"count": 0, "total": 0}
    }

    # Keywords related to assignments
    assignment_keywords = ["assignment", "homework",
                           "essay", "project", "paper", "report", "coursework"]

    # Process each interview
    for interview in interviews:
        if "responses" not in interview:
            continue

        responses = interview["responses"]

        # AI for learning
        if "ai_in_learning" in responses:
            themes["ai_for_learning"]["total"] += 1
            if responses["ai_in_learning"].get("uses_ai", False):
                themes["ai_for_learning"]["count"] += 1

            # Check for assignment-related keywords in AI usage
            ai_usage = responses["ai_in_learning"].get("ai_usage", [])
            themes["ai_for_assignments"]["total"] += 1
            if any(keyword in " ".join(ai_usage).lower() for keyword in assignment_keywords):
                themes["ai_for_assignments"]["count"] += 1

        # AI outside learning
        if "ai_outside_learning" in responses:
            themes["ai_outside_learning"]["total"] += 1
            if responses["ai_outside_learning"].get("uses_ai", False):
                themes["ai_outside_learning"]["count"] += 1

        # Attitudes toward AI
        if "sentiment_analysis" in interview and "education" in interview["sentiment_analysis"]:
            sentiment = interview["sentiment_analysis"]["education"]
            themes["attitudes"]["total"] += 1

            if "positive" in sentiment.lower():
                themes["attitudes"]["positive"] += 1
            elif "negative" in sentiment.lower():
                themes["attitudes"]["negative"] += 1
            else:
                themes["attitudes"]["neutral"] += 1

        # Concerns about AI
        if "concerns_about_ai" in responses:
            themes["concerns_about_ai"]["total"] += 1
            concerns = responses["concerns_about_ai"]
            if any(val for val in concerns.values() if val and val != ""):
                themes["concerns_about_ai"]["count"] += 1

    return themes


def get_percentage_range(percentage):
    """
    Convert percentage to a consistent range format

    Args:
        percentage (float): Percentage value

    Returns:
        str: Percentage range
    """
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


def format_demographic_table(demographic_stats, total_count):
    """
    Format demographic statistics as a markdown table

    Args:
        demographic_stats (dict): Demographic statistics
        total_count (int): Total number of interviews

    Returns:
        str: Markdown formatted demographic table
    """
    # Helper function to calculate percentages
    def calculate_percentages(counts, total):
        result = {}
        for key, count in counts.items():
            result[key] = {
                "count": count,
                "percentage": round((count / total) * 100)
            }
        return result

    # Process each demographic category
    gender_stats = calculate_percentages(
        demographic_stats["gender"], total_count)
    age_group_stats = calculate_percentages(
        demographic_stats["age_group"], total_count)
    college_stats = calculate_percentages(
        demographic_stats["college"], total_count)

    # Format subject list
    subjects_list = sorted(
        [(subject, count)
         for subject, count in demographic_stats["subjects"].items()],
        key=lambda x: x[1],
        reverse=True
    )

    # Format course types
    course_type_stats = calculate_percentages(
        demographic_stats["course_types"], total_count)

    # Build markdown table
    markdown = f"""
| Gender | Count | Percentage |
|--------|-------|------------|
"""
    for gender, stats in gender_stats.items():
        markdown += f"| {gender} | {stats['count']} | {stats['percentage']}% |\n"

    markdown += f"""
| College | Count | Percentage |
|---------|-------|------------|
"""
    for college, stats in college_stats.items():
        markdown += f"| {college} | {stats['count']} | {stats['percentage']}% |\n"

    markdown += f"""
| Age Group | Count | Percentage |
|-----------|-------|------------|
"""
    for age_group, stats in age_group_stats.items():
        markdown += f"| {age_group} | {stats['count']} | {stats['percentage']}% |\n"

    markdown += f"""
### Subjects Mentioned
"""
    for subject, count in subjects_list:
        markdown += f"- {subject} ({count})\n"

    markdown += f"""
| Course Type | Count | Percentage |
|-------------|-------|------------|
"""
    for course_type, stats in course_type_stats.items():
        markdown += f"| {course_type} | {stats['count']} | {stats['percentage']}% |\n"

    return markdown


def format_theme_analysis(theme_stats):
    """
    Format theme statistics as a markdown section

    Args:
        theme_stats (dict): Theme statistics

    Returns:
        str: Markdown formatted theme analysis
    """
    markdown = "\n### Key Themes\n\n"

    # AI for learning
    ai_learning_percent = round((theme_stats["ai_for_learning"]["count"] /
                                theme_stats["ai_for_learning"]["total"]) * 100) if theme_stats["ai_for_learning"]["total"] > 0 else 0
    ai_learning_range = get_percentage_range(ai_learning_percent)

    markdown += f"#### Using AI for Learning\n"
    markdown += f"{ai_learning_range} of students ({theme_stats['ai_for_learning']['count']}/{theme_stats['ai_for_learning']['total']}) "
    markdown += "reported using AI tools to support their learning.\n\n"

    # AI for assignments
    ai_assignments_percent = round((theme_stats["ai_for_assignments"]["count"] /
                                   theme_stats["ai_for_assignments"]["total"]) * 100) if theme_stats["ai_for_assignments"]["total"] > 0 else 0
    ai_assignments_range = get_percentage_range(ai_assignments_percent)

    markdown += f"#### Using AI for Assignments\n"
    markdown += f"{ai_assignments_range} of students ({theme_stats['ai_for_assignments']['count']}/{theme_stats['ai_for_assignments']['total']}) "
    markdown += "indicated they use AI for completing assignments and coursework.\n\n"

    # AI outside learning
    ai_outside_percent = round((theme_stats["ai_outside_learning"]["count"] /
                               theme_stats["ai_outside_learning"]["total"]) * 100) if theme_stats["ai_outside_learning"]["total"] > 0 else 0
    ai_outside_range = get_percentage_range(ai_outside_percent)

    markdown += f"#### Using AI Outside Learning\n"
    markdown += f"{ai_outside_range} of students ({theme_stats['ai_outside_learning']['count']}/{theme_stats['ai_outside_learning']['total']}) "
    markdown += "use AI tools outside of their academic work.\n\n"

    # Attitudes
    if theme_stats["attitudes"]["total"] > 0:
        positive_percent = round(
            (theme_stats["attitudes"]["positive"] / theme_stats["attitudes"]["total"]) * 100)
        neutral_percent = round(
            (theme_stats["attitudes"]["neutral"] / theme_stats["attitudes"]["total"]) * 100)
        negative_percent = round(
            (theme_stats["attitudes"]["negative"] / theme_stats["attitudes"]["total"]) * 100)

        positive_range = get_percentage_range(positive_percent)
        neutral_range = get_percentage_range(neutral_percent)
        negative_range = get_percentage_range(negative_percent)

        markdown += f"#### Attitudes Towards AI in Education\n"
        markdown += "Student attitudes toward AI in education were:\n"
        markdown += f"- Positive: {positive_range} ({theme_stats['attitudes']['positive']} students)\n"
        markdown += f"- Neutral: {neutral_range} ({theme_stats['attitudes']['neutral']} students)\n"
        markdown += f"- Negative: {negative_range} ({theme_stats['attitudes']['negative']} students)\n\n"

    # Concerns
    concerns_percent = round((theme_stats["concerns_about_ai"]["count"] /
                             theme_stats["concerns_about_ai"]["total"]) * 100) if theme_stats["concerns_about_ai"]["total"] > 0 else 0
    concerns_range = get_percentage_range(concerns_percent)

    markdown += f"#### Concerns About AI\n"
    markdown += f"{concerns_range} of students ({theme_stats['concerns_about_ai']['count']}/{theme_stats['concerns_about_ai']['total']}) "
    markdown += "expressed concerns about AI.\n"

    return markdown


def generate_consistent_meta_summary(interviews, normalise=True, show_normalisation=False):
    """
    Generate a meta-summary with consistent statistics

    Args:
        interviews (list): List of interview documents from MongoDB
        normalise (bool): Whether to normalise categorical values
        show_normalisation (bool): Whether to show normalisation details in the summary

    Returns:
        tuple: (formatted_summary, normalisation_info)
    """
    # Generate metadata for summary
    total_count = len(interviews)
    timestamp = datetime.now().strftime("%d %B %Y, %H:%M")

    # Process demographics with normalisation if requested
    demographic_stats, normalisation_info = calculate_demographic_stats(
        interviews, normalise)
    demographic_table = format_demographic_table(
        demographic_stats, total_count)

    # Process themes
    theme_stats = analyze_themes(interviews)
    theme_analysis = format_theme_analysis(theme_stats)

    # Combine into complete summary
    summary = f"""# Student Interview Analysis
Generated on {timestamp}
Based on analysis of {total_count} student interviews

## Demographics
{demographic_table}

## Thematic Analysis
{theme_analysis}
"""

    # Add normalisation notes if requested
    if normalise and show_normalisation:
        summary += """
## Data Normalisation Notes
The data in this summary has been normalised to group similar values together.
This improves accuracy by accounting for variations in spelling, capitalisation, and formatting.
For more details, see the 'Normalisation Details' section in the sidebar.
"""

    return summary, normalisation_info
