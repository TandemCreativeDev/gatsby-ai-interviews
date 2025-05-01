import re
from difflib import SequenceMatcher
import pandas as pd
from collections import defaultdict
import nltk
from nltk.stem import WordNetLemmatizer
import streamlit as st


def download_nltk_data():
    """Ensure necessary NLTK data is available"""
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet', quiet=True)


class DataNormaliser:
    """
    Class for normalising and clustering categorical data from interview responses
    """

    def __init__(self):
        # Initialize lemmatiser for word normalisation
        download_nltk_data()
        self.lemmatiser = WordNetLemmatizer()

        # Known category-specific patterns
        self.category_patterns = {
            'college': [
                (r'\bcollege\b', 'college'),  # Standardize "college" spelling
                # Remove "campus" for standardization
                (r'\bcampus\b', '')
            ],
            'subject': [
                (r'\blevel\s+\d+\b', ''),     # Remove "level X" indicators
                (r'\bbtec\b', ''),            # Remove qualification types
                (r'\ba-levels?\b', ''),       # Remove qualification types
                (r'\bt-levels?\b', '')        # Remove qualification types
            ]
        }

        # Domain-specific substitutions
        self.synonym_mappings = {
            'subject': {
                'graphic design': ['graphics', 'graphics and photography', 'graphic design visual communications'],
                'information technology': ['it', 'btec it'],
                'animal management': ['animal care', 'animal welfare', 'animal care and welfare'],
                'construction': ['multi-trade construction', 'multi trade'],
                'mathematics': ['maths', 'further maths', 'further mathematics'],
                'biology': ['bio'],
                'chemistry': ['chem'],
                'psychology': ['psych']
            }
        }

    def clean_text(self, text, category=None):
        """
        Clean and standardize text data

        Args:
            text (str): Text to clean
            category (str, optional): Category type for specific cleaning rules

        Returns:
            str: Cleaned and standardized text
        """
        if not text or not isinstance(text, str):
            return "Unknown"

        # Remove [redacted: ...] patterns
        text = re.sub(r'\[redacted:.*?\]', '', text)

        # Convert to lowercase
        text = text.lower()

        # Apply category-specific patterns
        if category and category in self.category_patterns:
            for pattern, replacement in self.category_patterns[category]:
                text = re.sub(pattern, replacement, text)

        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)

        # Standardize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def similarity_ratio(self, a, b):
        """Calculate string similarity ratio"""
        return SequenceMatcher(None, a, b).ratio()

    def apply_direct_mappings(self, values, category=None):
        """
        Apply known synonym mappings based on the category

        Args:
            values (list): List of values to normalise
            category (str): Category type (e.g., 'subject', 'college')

        Returns:
            list: Values with known mappings applied
        """
        if not category or category not in self.synonym_mappings:
            return values

        result = []
        for value in values:
            mapped = False
            for canonical, synonyms in self.synonym_mappings[category].items():
                if any(self.similarity_ratio(value, syn) > 0.9 for syn in synonyms):
                    result.append(canonical)
                    mapped = True
                    break
            if not mapped:
                result.append(value)

        return result

    def split_combined_subjects(self, value_list, category=None):
        """
        Split combined subjects into individual subjects

        Args:
            value_list (list): List of subject values to split
            category (str): Category type

        Returns:
            list: Expanded list with individual subjects
        """
        if category != 'subject':
            return value_list

        result = []

        # Common subject names to identify in combinations
        subjects = [
            'mathematics', 'maths', 'further maths', 'further mathematics',
            'biology', 'chemistry', 'physics', 'psychology', 'sociology',
            'english', 'history', 'geography', 'computer science',
            'business', 'economics', 'art', 'design', 'music'
        ]

        for value in value_list:
            if not value or value == "Unknown":
                result.append(value)
                continue

            # Check if this is a combined subject string
            value_lower = value.lower()

            # If contains 'and' or multiple subjects from our list, split it
            contains_multiple = ('and' in value_lower) or sum(1 for subj in subjects if subj in value_lower) > 1

            if contains_multiple:
                # Split by common separators
                words = re.split(r'\s+and\s+|\s+&\s+|,\s*', value_lower)

                # Also check for subject names directly in the value
                for subject in subjects:
                    if subject in value_lower and not any(subject in word for word in words):
                        words.append(subject)

                # Add each identified subject to results
                for word in words:
                    if word and word.strip():
                        result.append(word.strip())
            else:
                result.append(value)

        return result

    def cluster_similar_values(self, value_list, category=None, threshold=0.85):
        """
        Group similar values together using fuzzy matching

        Args:
            value_list (list): List of values to cluster
            category (str): Category type for specific cleaning rules
            threshold (float): Similarity threshold (0-1)

        Returns:
            tuple: (standardized_map, cluster_info)
                standardized_map: dict mapping original values to standardized values
                cluster_info: dict with statistics about the clustering
        """
        if not value_list:
            return {}, {}

        # First pass: clean and standardize all values
        cleaned_values = [self.clean_text(val, category) for val in value_list]

        # Split combined subjects if needed
        if category == 'subject':
            cleaned_values = self.split_combined_subjects(cleaned_values, category)

        # Apply known synonym mappings if available
        cleaned_values = self.apply_direct_mappings(cleaned_values, category)

        # Count frequencies to prioritize more common values
        value_counts = pd.Series(cleaned_values).value_counts()

        # Create clusters
        clusters = []
        assigned = set()

        # Sort by frequency
        sorted_values = list(value_counts.index)

        # Cluster similar values
        for i, val1 in enumerate(sorted_values):
            if val1 in assigned or val1 == "Unknown":
                continue

            # Create a new cluster
            cluster = [val1]
            assigned.add(val1)

            # Find similar values
            for val2 in sorted_values:
                if val2 in assigned or val2 == "Unknown":
                    continue

                # Check similarity
                if self.similarity_ratio(val1, val2) > threshold:
                    cluster.append(val2)
                    assigned.add(val2)

            if cluster:
                clusters.append(cluster)

        # Create mapping from cleaned value to canonical value
        mapping = {}
        for cluster in clusters:
            if not cluster:
                continue

            # Find most frequent value in the cluster
            cluster_counts = {val: value_counts.get(val, 0) for val in cluster}
            canonical = max(cluster_counts, key=cluster_counts.get)

            # Format canonical name nicely for display
            display_name = ' '.join(word.capitalize()
                                    for word in canonical.split())

            # Map all values in cluster to the canonical form
            for val in cluster:
                mapping[val] = display_name

        # Create mapping from original to canonical
        original_to_canonical = {}
        cluster_info = defaultdict(list)

        for i, original in enumerate(value_list):
            if i < len(cleaned_values):
                cleaned = cleaned_values[i]
                if cleaned == "Unknown":
                    canonical = "Unknown"
                else:
                    canonical = mapping.get(cleaned,
                                            ' '.join(word.capitalize() for word in cleaned.split()))

                original_to_canonical[original] = ' '.join(word.capitalize() for word in canonical.split())
                cluster_info[canonical].append(original)

        return original_to_canonical, dict(cluster_info)

    def normalise_field_values(self, documents, field_path, category=None):
        """
        Extract and normalise values from a specific field in documents

        Args:
            documents (list): List of documents
            field_path (str): Path to the field (dot notation, e.g., 'responses.about_user.study_field')
            category (str): Category type for specific normalisation rules

        Returns:
            tuple: (normalised_values, mapping, cluster_info)
                normalised_values: list of normalised values for each document
                mapping: dict mapping original values to normalised values
                cluster_info: dict with information about each cluster
        """
        # Extract values from the specified field path
        values = []
        for doc in documents:
            value = doc
            for key in field_path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            values.append(value if value else "Unknown")

        # Normalise the values
        mapping, cluster_info = self.cluster_similar_values(values, category)

        # Apply the mapping to get normalised values
        normalised_values = [mapping.get(val, "Unknown") for val in values]

        return normalised_values, mapping, cluster_info

    def extract_subjects_from_transcripts(self, documents):
        """
        Extract individual subjects from study fields and transcripts

        Args:
            documents (list): List of interview documents

        Returns:
            dict: Dictionary with subject counts
        """
        subject_mentions = defaultdict(int)

        # Common subject names to look for
        subject_patterns = {
            'Mathematics': [r'\bmaths\b', r'\bmathematics\b', r'\bfurther maths\b'],
            'Biology': [r'\bbiology\b', r'\bbio\b'],
            'Chemistry': [r'\bchemistry\b', r'\bchem\b'],
            'Physics': [r'\bphysics\b'],
            'Psychology': [r'\bpsychology\b', r'\bpsych\b'],
            'English': [r'\benglish\b'],
            'Computer Science': [r'\bcomputer science\b', r'\bcomputing\b', r'\bIT\b', r'\binformation technology\b'],
            'Business': [r'\bbusiness\b', r'\beconomics\b'],
            'Art & Design': [r'\bart\b', r'\bdesign\b', r'\bgraphics\b', r'\bgraphic design\b'],
            'History': [r'\bhistory\b'],
            'Geography': [r'\bgeography\b'],
            'Sociology': [r'\bsociology\b'],
            'Health & Social Care': [r'\bhealth\b', r'\bsocial care\b', r'\bhealthcare\b'],
            'Engineering': [r'\bengineering\b'],
            'Media': [r'\bmedia\b', r'\bjournalism\b'],
            'Sport': [r'\bsport\b', r'\bpe\b', r'\bphysical education\b'],
            'Animal Management': [r'\banimal\b']
        }

        for doc in documents:
            # Get study field from responses if available
            study_field = None
            if ("responses" in doc and
                "about_user" in doc["responses"] and
                    "study_field" in doc["responses"]["about_user"]):
                study_field = doc["responses"]["about_user"]["study_field"]

            # Get transcript text
            transcript = doc.get("transcript", "")

            # Combine for analysis
            text_to_analyze = ""
            if study_field:
                text_to_analyze += study_field + " "
            if transcript:
                text_to_analyze += transcript

            text_to_analyze = text_to_analyze.lower()

            # Count subject mentions
            for subject, patterns in subject_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_to_analyze):
                        subject_mentions[subject] += 1
                        break  # Only count each subject once per document

        return dict(subject_mentions)

    def normalise_college_names(self, documents):
        """
        Normalises college names with enhanced pattern matching for UK educational institutions

        Args:
            documents (list): List of interview documents

        Returns:
            dict: Statistics with normalised college names
        """
        # Extract all college names
        college_values = [doc.get("college", "Unknown") for doc in documents]

        # Specialized cleaning patterns for educational institutions
        college_specific_patterns = [
            # Remove campus/site indicators
            (r'\b(campus|buddy|site|centre|center)\b', ''),
            # Remove location qualifiers when redundant
            (r'(\w+)(\s+\w+)\s+\1', r'\1\2'),
            # Standardize college/university terminology
            (r'\bcollege of\b', 'college'),
            (r'\buniversity of\b', 'university'),
            # Fix common typos
            (r'\bcrencester\b', 'cirencester'),
            # Fix known abbreviations and normalise case
            (r'\bbmet\b', 'Birmingham Metropolitan'),
            (r'\bTes\b', 'TES'),
        ]

        # Enhanced cleaning for college names
        cleaned_colleges = []
        for college in college_values:
            if not college or not isinstance(college, str):
                cleaned_colleges.append("Unknown")
                continue

            # Check for redacted content
            if re.search(r'\[redacted', college, re.IGNORECASE):
                # Only keep known college names in redacted text
                if "fareham" in college.lower():
                    college = "Fareham College"
                elif "newcastle" in college.lower():
                    college = "Newcastle College"
                elif "moulton" in college.lower():
                    college = "Moulton College"
                elif "bishop burton" in college.lower():
                    college = "Bishop Burton College"
                elif "bmet" in college.lower():
                    college = "BMET College"
                else:
                    # If no known college name found in redacted text, mark as Unknown
                    cleaned_colleges.append("Unknown")
                    continue

            # Apply college-specific cleaning patterns
            college = college.strip()
            for pattern, replacement in college_specific_patterns:
                college = re.sub(pattern, replacement, college, flags=re.IGNORECASE)

            # Remove common suffixes that don't add disambiguation value
            college = re.sub(r'\s+(college|university|institute|school)$', '', college, flags=re.IGNORECASE)

            # Standardize whitespace
            college = re.sub(r'\s+', ' ', college).strip()

            # For specific problematic cases
            if re.search(r'^fareham\b', college, re.IGNORECASE):
                college = "Fareham College"
            elif re.search(r'^farmham\b', college, re.IGNORECASE):  # Handle typo in Fareham
                college = "Fareham College"
            elif re.search(r'\bmoulton\b', college, re.IGNORECASE):
                college = "Moulton College"
            elif re.search(r'\bbishop\s*burton\b|\bbishopburton\b', college, re.IGNORECASE):
                college = "Bishop Burton College"
            elif re.search(r'\bnewcastle\b', college, re.IGNORECASE):
                college = "Newcastle College"
            elif re.search(r'\balex\b', college, re.IGNORECASE):
                # Assuming Alex Stanbury is a person, not a college
                college = "Unknown"
            elif re.search(r'\bcapital city\b', college, re.IGNORECASE):
                college = "Capital City College"
            elif re.search(r'\bcircencester\b|\bcirencester\b', college, re.IGNORECASE):
                college = "Cirencester College"

            # Proper case (title case) while preserving known abbreviations
            if college.lower() not in ["unknown", "tes"]:
                if college.lower() == "bmet":
                    college = "BMET College"
                else:
                    college = ' '.join(word.capitalize() for word in college.lower().split())

            # Add College suffix if missing and name is short
            if (len(college.split()) == 1 and
                college.lower() not in ["unknown", "tes"] and
                "college" not in college.lower() and
                    "university" not in college.lower()):
                college = f"{college} College"

            # Add cleaned college to list
            cleaned_colleges.append(college if college else "Unknown")

        # Create a direct mapping dictionary
        college_stats = {}
        for college in cleaned_colleges:
            if college not in college_stats:
                college_stats[college] = 0
            college_stats[college] += 1

        # Sort colleges by count
        sorted_stats = dict(sorted(college_stats.items(), key=lambda item: item[1], reverse=True))

        return sorted_stats

    def generate_stats_with_normalised_values(self, documents):
        """
        Generate statistics with normalised categorical values and create document update list

        Args:
            documents (list): List of interview documents

        Returns:
            tuple: (statistics dict, list of document update dicts)
        """
        import re
        from collections import defaultdict

        stats = {
            "gender": {},
            "college": {},
            "age_group": {},
            "subjects": {},
            "course_types": {}
        }

        # List to collect document updates
        docs_to_update = []

        # Use enhanced college normalisation
        stats["college"] = self.normalise_college_names(documents)

        # Normalise and count gender
        _, _, gender_clusters = self.normalise_field_values(documents, "gender", "gender")
        stats["gender"] = {}

        # Normalise and count age groups
        _, _, age_clusters = self.normalise_field_values(documents, "age_group", "age_group")
        stats["age_group"] = {}

        # Common subject names to look for
        subject_patterns = {
            'Mathematics': [r'\bmaths\b', r'\bmathematics\b', r'\bfurther maths\b'],
            'Biology': [r'\bbiology\b', r'\bbio\b'],
            'Chemistry': [r'\bchemistry\b', r'\bchem\b'],
            'Physics': [r'\bphysics\b'],
            'Psychology': [r'\bpsychology\b', r'\bpsych\b'],
            'English': [r'\benglish\b'],
            'Computer Science': [r'\bcomputer science\b', r'\bcomputing\b', r'\bIT\b', r'\binformation technology\b'],
            'Business': [r'\bbusiness\b', r'\beconomics\b'],
            'Art & Design': [r'\bart\b', r'\bdesign\b', r'\bgraphics\b', r'\bgraphic design\b'],
            'History': [r'\bhistory\b'],
            'Geography': [r'\bgeography\b'],
            'Sociology': [r'\bsociology\b'],
            'Health & Social Care': [r'\bhealth\b', r'\bsocial care\b', r'\bhealthcare\b'],
            'Engineering': [r'\bengineering\b'],
            'Media': [r'\bmedia\b', r'\bjournalism\b'],
            'Sport': [r'\bsport\b', r'\bpe\b', r'\bphysical education\b'],
            'Animal Management': [r'\banimal\b']
        }

        # Course type patterns
        course_patterns = {
            "A-levels": r'\b[aA][\s-]levels?\b|\b[aA] level\b',
            "BTECs": r'\bbtecs?\b|\bBTECs?\b',
            "Apprenticeships": r'\bapprenticeships?\b|\bApprenticeships?\b',
            "T-levels": r'\b[tT][\s-]levels?\b|\b[tT] level\b'
        }

        # Extract subjects for all documents and track in stats
        subject_mentions = defaultdict(int)

        for doc in documents:
            # Initialize update dict with document ID
            update_doc = doc.copy()

            # Process gender
            gender = "Unknown"
            if "gender" in doc and doc["gender"]:
                gender = doc["gender"].strip()
            elif "responses" in doc and doc["responses"] and "about_user" in doc["responses"]:
                about_user = doc["responses"]["about_user"]
                if "gender" in about_user:
                    if "female" in about_user["gender"].lower():
                        gender = "Female"
                    elif "male" in about_user["gender"].lower():
                        gender = "Male"
                    elif "binary" in about_user["gender"].lower():
                        gender = "Non-binary"

            update_doc["gender"] = gender

            if gender not in stats["gender"]:
                stats["gender"][gender] = 0
            stats["gender"][gender] += 1

            # Process age group
            age_group = "Unknown"
            if "age_group" in doc and doc["age_group"]:
                age_group = doc["age_group"].strip()
            elif "responses" in doc and doc["responses"] and "about_user" in doc["responses"]:
                about_user = doc["responses"]["about_user"]
                if "over_25" in about_user:
                    age_group = "Over 25" if about_user["over_25"] else "Under 25"

            update_doc["age_group"] = age_group

            if age_group not in stats["age_group"]:
                stats["age_group"][age_group] = 0
            stats["age_group"][age_group] += 1

            # Process college
            college = "Unknown"
            if "college" in doc and doc["college"]:
                original_college = doc["college"].strip()
                college = original_college

                for cluster_name, variations in gender_clusters.items():
                    if original_college.lower() in [v.lower() for v in variations]:
                        college = cluster_name
                        break

            update_doc["college"] = college

            # Process subjects
            doc_subjects = []

            # Get study field from responses if available
            study_field = None
            if ("responses" in doc and
                "about_user" in doc["responses"] and
                    "study_field" in doc["responses"]["about_user"]):
                study_field = doc["responses"]["about_user"]["study_field"]

            # Get transcript text
            transcript = doc.get("transcript", "")

            # Combine for analysis
            text_to_analyze = ""
            if study_field:
                text_to_analyze += study_field + " "
            if transcript:
                text_to_analyze += transcript
            text_to_analyze = text_to_analyze.lower()

            # Find subjects mentioned in this document
            for subject, patterns in subject_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_to_analyze):
                        doc_subjects.append(subject)
                        subject_mentions[subject] += 1
                        break  # Only count each subject once per document

            update_doc["subjects"] = doc_subjects

            # Process course types
            doc_course_types = []

            if transcript:
                for course_type, pattern in course_patterns.items():
                    if re.search(pattern, transcript):
                        doc_course_types.append(course_type)
                        stats["course_types"][course_type] = stats["course_types"].get(
                            course_type, 0) + 1

            update_doc["course_types"] = doc_course_types

            # Add document to update list
            docs_to_update.append(update_doc)

        # Update overall stats
        stats["subjects"] = dict(subject_mentions)

        return stats, docs_to_update

    def show_normalisation_details(self, cluster_info, category_name):
        """
        Display normalisation details in Streamlit

        Args:
            cluster_info (dict): Cluster information
            category_name (str): Name of the category being normalised
        """
        st.subheader(f"{category_name} Normalisation Details")

        # Sort clusters by size
        sorted_clusters = sorted(
            cluster_info.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        for canonical, originals in sorted_clusters:
            if len(originals) > 1:  # Only show groups with multiple variations
                with st.expander(f"{canonical} ({len(originals)} variations)"):
                    for original in originals:
                        st.write(f"- \"{original}\"")
