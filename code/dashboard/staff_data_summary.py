from datetime import datetime
from collections import defaultdict


def calculate_demographic_stats(interviews):
    """
    Calculate demographic statistics from staff interview documents using normalized data

    Args:
        interviews (list): List of interview documents from MongoDB

    Returns:
        dict: Demographics statistics
    """
    # Initialize stats dictionary
    stats = {
        "college": defaultdict(int),
        "role": defaultdict(int),
        "subjects": defaultdict(int),
        "departments": defaultdict(int)
    }

    # Process each interview to collect demographic data
    for doc in interviews:
        # Count college
        college = doc.get("college", "Unknown")
        stats["college"][college] += 1

        # Count role
        role = doc.get("role", "Unknown")
        stats["role"][role] += 1

        # Count subjects from the new normalized 'subjects' field we added
        for subject in doc.get("subjects", []):
            stats["subjects"][subject] += 1

        # Count department from the new 'department' field we added
        department = doc.get("department", "Unknown")
        stats["departments"][department] += 1

    # Convert defaultdicts to regular dicts for cleaner output
    return {
        "college": dict(stats["college"]),
        "role": dict(stats["role"]),
        "subjects": dict(stats["subjects"]),
        "departments": dict(stats["departments"])
    }


def get_original_subjects(doc):
    """Extract subjects from specific fields in the document, not from tags."""
    subjects = []

    # First check if we have an "original_subjects" field directly (from logs)
    if "original_subjects" in doc and isinstance(doc["original_subjects"], list):
        subjects.extend(doc["original_subjects"])

    # Then check teaching_and_learning in staff_analysis
    if "staff_analysis" in doc and "teaching_and_learning" in doc["staff_analysis"]:
        curriculum = doc["staff_analysis"]["teaching_and_learning"].get("curriculum_enhancement", {})
        if "subject_specific_applications" in curriculum and isinstance(curriculum["subject_specific_applications"], list):
            subjects.extend(curriculum["subject_specific_applications"])

    # Then check teaching_and_learning in responses
    if "responses" in doc and "teaching_and_learning" in doc["responses"]:
        curriculum = doc["responses"]["teaching_and_learning"].get("curriculum_enhancement", {})
        if "subject_specific_applications" in curriculum and isinstance(curriculum["subject_specific_applications"], list):
            subjects.extend(curriculum["subject_specific_applications"])

    # If no subjects found, fall back to tags as subjects
    if not subjects and "tags" in doc and isinstance(doc["tags"], list):
        subjects.extend(doc["tags"])
        # Optional: Add a print to show when we're using tags as fallback
        print(f"No subjects found for {doc.get('username', 'Unknown')}, using tags as fallback: {doc['tags']}")

    return subjects


def analyse_themes(interviews):
    """
    Analyse themes from staff interview documents using the normalized fields

    Args:
        interviews (list): List of interview documents from MongoDB

    Returns:
        dict: Theme statistics
    """
    # Initialize theme counters
    themes = {
        "ai_for_teaching": {"count": 0, "total": 0},
        "ai_for_work": {"count": 0, "total": 0},
        "ai_outside_education": {"count": 0, "total": 0},
        "attitudes": {"positive": 0, "neutral": 0, "negative": 0, "total": 0},
        "concerns_about_ai": {"count": 0, "total": 0},
        "barriers_to_adoption": {"count": 0, "total": 0},
        "training_needs": {"count": 0, "total": 0}
    }

    # Enhanced keywords for identifying specific themes in subjects
    teaching_ai_keywords = [
        "teach", "educat", "learn", "class", "lesson", "curriculum",
        "assessment", "grade", "personaliz", "student", "instruction",
        "pedagog", "tutor", "lecture", "course", "stem", "material",
        "AI for Teaching", "AI for Assessment", "AI for Personalized Learning",
        "Curriculum Planning", "STEM Education"
    ]

    work_ai_keywords = [
        "admin", "management", "planning", "workflow", "tool", "office",
        "document", "data", "analysis", "report", "implementation",
        "strateg", "meeting", "schedule", "organiz", "productivity",
        "AI for Administration", "AI Tools", "AI Fundamentals", "Strategic Planning",
        "Implementation Planning", "Data Analysis"
    ]

    outside_education_keywords = [
        "home", "personal", "hobby", "leisure", "entertainment", "social media",
        "gaming", "creative", "art", "music", "travel", "shopping", "finance",
        "health", "fitness", "family", "chat"
    ]

    # Process each interview
    for interview in interviews:
        # Get normalized subjects
        subjects = interview.get("subjects", []).copy()  # Make a copy to avoid modifying the original

        # Extend with original subjects - correctly adding individual items
        original_subjects = get_original_subjects(interview)
        subjects.extend(original_subjects)

        # Remove any duplicate subjects
        subjects = list(set(subjects))

        # AI for teaching - check if they have teaching-related AI subjects using partial matching
        themes["ai_for_teaching"]["total"] += 1
        if any(any(keyword.lower() in subject.lower() for keyword in teaching_ai_keywords) for subject in subjects):
            themes["ai_for_teaching"]["count"] += 1

        # Alternatively, check the transcript fields for teaching usage
        if themes["ai_for_teaching"]["count"] == 0:
            teaching_found = False

            # Check staff_analysis
            if "staff_analysis" in interview and "teaching_and_learning" in interview["staff_analysis"]:
                teaching_data = interview["staff_analysis"]["teaching_and_learning"]
                if teaching_data and any(isinstance(teaching_data.get(k), list) and len(teaching_data.get(k, [])) > 0
                                         for k in ["curriculum_enhancement", "assessment_methods", "personalized_learning"]):
                    teaching_found = True

            # Check responses
            if not teaching_found and "responses" in interview and "teaching_and_learning" in interview["responses"]:
                teaching_data = interview["responses"]["teaching_and_learning"]
                if teaching_data and any(isinstance(teaching_data.get(k), list) and len(teaching_data.get(k, [])) > 0
                                         for k in ["curriculum_enhancement", "assessment_methods", "personalized_learning"]):
                    teaching_found = True

            if teaching_found:
                themes["ai_for_teaching"]["count"] += 1

        # AI for work - check if they have work-related AI subjects using partial matching
        themes["ai_for_work"]["total"] += 1
        if any(any(keyword.lower() in subject.lower() for keyword in work_ai_keywords) for subject in subjects):
            themes["ai_for_work"]["count"] += 1

        # Alternatively, check the transcript fields for work usage
        if themes["ai_for_work"]["count"] == 0:
            work_found = False

            # Check staff_analysis
            if "staff_analysis" in interview and "administrative_applications" in interview["staff_analysis"]:
                admin_data = interview["staff_analysis"]["administrative_applications"]
                if admin_data and any(isinstance(admin_data.get(k), list) and len(admin_data.get(k, [])) > 0
                                      for k in ["efficiency_improvements", "data_analysis", "resource_allocation"]):
                    work_found = True

            # Check responses
            if not work_found and "responses" in interview and "administrative_applications" in interview["responses"]:
                admin_data = interview["responses"]["administrative_applications"]
                if admin_data and any(isinstance(admin_data.get(k), list) and len(admin_data.get(k, [])) > 0
                                      for k in ["efficiency_improvements", "data_analysis", "resource_allocation"]):
                    work_found = True

            if work_found:
                themes["ai_for_work"]["count"] += 1

        # AI outside education - check if they have outside-education related AI subjects using partial matching
        themes["ai_outside_education"]["total"] += 1
        if any(any(keyword.lower() in subject.lower() for keyword in outside_education_keywords) for subject in subjects):
            themes["ai_outside_education"]["count"] += 1

        # Also check transcript/responses for personal AI usage
        if themes["ai_outside_education"]["count"] == 0:
            outside_ai_found = False

            # Check staff_analysis
            if "staff_analysis" in interview and "personal_ai_usage" in interview["staff_analysis"]:
                personal_usage = interview["staff_analysis"]["personal_ai_usage"]
                if personal_usage and any(personal_usage.values()):
                    outside_ai_found = True

            # Check responses
            if not outside_ai_found and "responses" in interview and "personal_ai_usage" in interview["responses"]:
                personal_usage = interview["responses"]["personal_ai_usage"]
                if personal_usage and any(personal_usage.values()):
                    outside_ai_found = True

            if outside_ai_found:
                themes["ai_outside_education"]["count"] += 1

        # Attitudes toward AI
        themes["attitudes"]["total"] += 1

        # Check sentiment analysis from different locations
        sentiment = None

        # Direct sentiment_analysis field
        if "sentiment_analysis" in interview:
            sentiment = interview["sentiment_analysis"]
        # Check staff_analysis sentiment
        elif "staff_analysis" in interview and "sentiment_analysis" in interview["staff_analysis"]:
            sentiment = interview["staff_analysis"]["sentiment_analysis"]
        # Check responses sentiment
        elif "responses" in interview and "sentiment_analysis" in interview["responses"]:
            sentiment = interview["responses"]["sentiment_analysis"]

        if sentiment and "overall" in sentiment:
            overall = sentiment["overall"].lower()
            if "positive" in overall or "optimistic" in overall:
                themes["attitudes"]["positive"] += 1
            elif "negative" in overall or "pessimistic" in overall:
                themes["attitudes"]["negative"] += 1
            else:
                themes["attitudes"]["neutral"] += 1
        else:
            # If no sentiment found, default to neutral
            themes["attitudes"]["neutral"] += 1

        # Concerns about AI
        themes["concerns_about_ai"]["total"] += 1

        # Check for concerns from different locations
        concerns_found = False

        # Check staff_analysis
        if "staff_analysis" in interview and "stakeholder_perspectives" in interview["staff_analysis"]:
            concerns = interview["staff_analysis"]["stakeholder_perspectives"].get("teacher_views", {}).get("concerns", [])
            if concerns:
                concerns_found = True

        # Check responses
        if not concerns_found and "responses" in interview and "stakeholder_perspectives" in interview["responses"]:
            concerns = interview["responses"]["stakeholder_perspectives"].get("teacher_views", {}).get("concerns", [])
            if concerns:
                concerns_found = True

        # Also check implementation considerations risks
        if not concerns_found:
            risks = []
            if "staff_analysis" in interview and "implementation_considerations" in interview["staff_analysis"]:
                risks = interview["staff_analysis"]["implementation_considerations"].get("risks_and_mitigations", {}).get("identified_risks", [])
            elif "responses" in interview and "implementation_considerations" in interview["responses"]:
                risks = interview["responses"]["implementation_considerations"].get("risks_and_mitigations", {}).get("identified_risks", [])

            if risks:
                concerns_found = True

        if concerns_found:
            themes["concerns_about_ai"]["count"] += 1

        # Barriers to adoption
        themes["barriers_to_adoption"]["total"] += 1

        # Check for barriers from different locations
        barriers_found = False

        # Check staff_analysis
        if "staff_analysis" in interview and "stakeholder_perspectives" in interview["staff_analysis"]:
            barriers = interview["staff_analysis"]["stakeholder_perspectives"].get("teacher_views", {}).get("adoption_barriers", [])
            if barriers:
                barriers_found = True

        # Check responses
        if not barriers_found and "responses" in interview and "stakeholder_perspectives" in interview["responses"]:
            barriers = interview["responses"]["stakeholder_perspectives"].get("teacher_views", {}).get("adoption_barriers", [])
            if barriers:
                barriers_found = True

        if barriers_found:
            themes["barriers_to_adoption"]["count"] += 1

        # Training needs
        themes["training_needs"]["total"] += 1

        # Check for training needs from different locations
        training_found = False

        # Check staff_analysis
        if "staff_analysis" in interview and "stakeholder_perspectives" in interview["staff_analysis"]:
            training = interview["staff_analysis"]["stakeholder_perspectives"].get("teacher_views", {}).get("training_needs", [])
            if training:
                training_found = True

        # Check responses
        if not training_found and "responses" in interview and "stakeholder_perspectives" in interview["responses"]:
            training = interview["responses"]["stakeholder_perspectives"].get("teacher_views", {}).get("training_needs", [])
            if training:
                training_found = True

        # Also check support staff training
        if not training_found:
            support_training = []
            if "staff_analysis" in interview and "stakeholder_perspectives" in interview["staff_analysis"]:
                support_training = interview["staff_analysis"]["stakeholder_perspectives"].get("support_staff_role", {}).get("training_requirements", [])
            elif "responses" in interview and "stakeholder_perspectives" in interview["responses"]:
                support_training = interview["responses"]["stakeholder_perspectives"].get("support_staff_role", {}).get("training_requirements", [])

            if support_training:
                training_found = True

        if training_found:
            themes["training_needs"]["count"] += 1

    return themes


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
                "percentage": round((count / total) * 100) if total > 0 else 0
            }
        return result

    # Process each demographic category
    role_stats = calculate_percentages(demographic_stats["role"], total_count)
    college_stats = calculate_percentages(demographic_stats["college"], total_count)

    # Format subjects list
    subjects_list = sorted(
        [(subject, count) for subject, count in demographic_stats["subjects"].items()],
        key=lambda x: x[1],
        reverse=True
    )

    # Format departments
    department_stats = calculate_percentages(demographic_stats["departments"], total_count)

    # Build markdown table
    markdown = """
| College | Count | Percentage |
|---------|-------|------------|
"""
    for college, stats in college_stats.items():
        markdown += f"| {college} | {stats['count']} | {stats['percentage']}% |\n"

    markdown += """
| Staff Role | Count | Percentage |
|------------|-------|------------|
"""
    for role, stats in role_stats.items():
        markdown += f"| {role} | {stats['count']} | {stats['percentage']}% |\n"

    # Department section
    markdown += """
| Department | Count | Percentage |
|------------|-------|------------|
"""
    for dept, stats in department_stats.items():
        markdown += f"| {dept} | {stats['count']} | {stats['percentage']}% |\n"

    # Subjects section
    markdown += """
### Subjects
"""
    for subject, count in subjects_list:
        markdown += f"- {subject} ({count})\n"

    return markdown


def format_theme_analysis(theme_stats):
    """
    Format theme statistics as a markdown section

    Args:
        theme_stats (dict): Theme statistics

    Returns:
        str: Markdown formatted theme analysis
    """
    markdown = ""

    # AI for teaching
    ai_teaching_percent = round((theme_stats["ai_for_teaching"]["count"] /
                                 theme_stats["ai_for_teaching"]["total"]) * 100) if theme_stats["ai_for_teaching"]["total"] > 0 else 0

    markdown += "##### Using AI for Teaching\n"
    markdown += f"{ai_teaching_percent}% of staff ({theme_stats['ai_for_teaching']['count']}/{theme_stats['ai_for_teaching']['total']}) "
    markdown += "reported using or planning to use AI tools to support teaching activities.\n\n"

    # AI for work
    ai_work_percent = round((theme_stats["ai_for_work"]["count"] /
                             theme_stats["ai_for_work"]["total"]) * 100) if theme_stats["ai_for_work"]["total"] > 0 else 0

    markdown += "##### Using AI for Work\n"
    markdown += f"{ai_work_percent}% of staff ({theme_stats['ai_for_work']['count']}/{theme_stats['ai_for_work']['total']}) "
    markdown += "indicated they use or plan to use AI tools for work-related tasks.\n\n"

    # AI outside education
    ai_outside_percent = round((theme_stats["ai_outside_education"]["count"] /
                                theme_stats["ai_outside_education"]["total"]) * 100) if theme_stats["ai_outside_education"]["total"] > 0 else 0

    markdown += "##### Using AI Outside Education\n"
    markdown += f"{ai_outside_percent}% of staff ({theme_stats['ai_outside_education']['count']}/{theme_stats['ai_outside_education']['total']}) "
    markdown += "use AI tools outside of their educational work.\n\n"

    # Attitudes
    if theme_stats["attitudes"]["total"] > 0:
        positive_percent = round((theme_stats["attitudes"]["positive"] / theme_stats["attitudes"]["total"]) * 100)
        neutral_percent = round((theme_stats["attitudes"]["neutral"] / theme_stats["attitudes"]["total"]) * 100)
        negative_percent = round((theme_stats["attitudes"]["negative"] / theme_stats["attitudes"]["total"]) * 100)

        markdown += "##### Attitudes Towards AI in Education\n"
        markdown += "Staff attitudes toward AI in education were:\n"
        markdown += f"- Positive: {positive_percent}% ({theme_stats['attitudes']['positive']} staff members)\n"
        markdown += f"- Neutral: {neutral_percent}% ({theme_stats['attitudes']['neutral']} staff members)\n"
        markdown += f"- Negative: {negative_percent}% ({theme_stats['attitudes']['negative']} staff members)\n\n"

    # Concerns
    concerns_percent = round((theme_stats["concerns_about_ai"]["count"] /
                              theme_stats["concerns_about_ai"]["total"]) * 100) if theme_stats["concerns_about_ai"]["total"] > 0 else 0

    markdown += "##### Concerns About AI\n"
    markdown += f"{concerns_percent}% of staff ({theme_stats['concerns_about_ai']['count']}/{theme_stats['concerns_about_ai']['total']}) "
    markdown += "expressed concerns about AI in education.\n\n"

    # Barriers to adoption
    barriers_percent = round((theme_stats["barriers_to_adoption"]["count"] /
                              theme_stats["barriers_to_adoption"]["total"]) * 100) if theme_stats["barriers_to_adoption"]["total"] > 0 else 0

    markdown += "##### Barriers to AI Adoption\n"
    markdown += f"{barriers_percent}% of staff ({theme_stats['barriers_to_adoption']['count']}/{theme_stats['barriers_to_adoption']['total']}) "
    markdown += "identified barriers to adopting AI in their educational institution.\n\n"

    # Training needs
    training_percent = round((theme_stats["training_needs"]["count"] /
                              theme_stats["training_needs"]["total"]) * 100) if theme_stats["training_needs"]["total"] > 0 else 0

    markdown += "##### Training Needs for AI\n"
    markdown += f"{training_percent}% of staff ({theme_stats['training_needs']['count']}/{theme_stats['training_needs']['total']}) "
    markdown += "indicated specific training needs related to AI implementation.\n"

    return markdown


def generate_staff_summary(interviews):
    """
    Generate a summary of staff interview data using normalized fields

    Args:
        interviews (list): List of interview documents from MongoDB

    Returns:
        str: Formatted summary markdown
    """
    # Generate metadata for summary
    total_count = len(interviews)
    timestamp = datetime.now().strftime("%d %B %Y, %H:%M")

    # Calculate demographic statistics directly from normalized fields
    demographic_stats = calculate_demographic_stats(interviews)
    demographic_table = format_demographic_table(demographic_stats, total_count)

    # Process themes
    theme_stats = analyse_themes(interviews)
    theme_analysis = format_theme_analysis(theme_stats)

    # Combine into complete summary
    summary = f"""# Staff Interview Analysis
Generated on {timestamp}
Based on analysis of {total_count} staff interviews

#### Demographics
{demographic_table}

#### Thematic Analysis
{theme_analysis}
"""

    return summary
