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

        # Domain-specific substitutions (based on your example)
        self.synonym_mappings = {
            'subject': {
                'graphic design': ['graphics', 'graphics and photography', 'graphic design visual communications'],
                'information technology': ['it', 'btec it'],
                'biology chemistry mathematics': ['biology chemistry maths', 'chemistry biology maths'],
                'animal management': ['animal care', 'animal welfare', 'animal care and welfare'],
                'construction': ['multi-trade construction', 'multi trade']
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

                original_to_canonical[original] = canonical
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

    def generate_stats_with_normalised_values(self, documents):
        """
        Generate statistics with normalised categorical values

        Args:
            documents (list): List of interview documents

        Returns:
            dict: Statistics with normalised values
        """
        stats = {
            "gender": {},
            "college": {},
            "age_group": {},
            "subjects": {},
            "course_types": {}
        }

        # Normalise colleges
        _, _, college_clusters = self.normalise_field_values(
            documents, "college", "college")

        # Count normalised colleges
        for college, originals in college_clusters.items():
            stats["college"][college] = len(originals)

        # Normalise and count genders
        _, _, gender_clusters = self.normalise_field_values(
            documents, "gender", "gender")

        for gender, originals in gender_clusters.items():
            stats["gender"][gender] = len(originals)

        # Normalise and count age groups
        _, _, age_clusters = self.normalise_field_values(
            documents, "age_group", "age_group")

        for age, originals in age_clusters.items():
            stats["age_group"][age] = len(originals)

        # Extract and normalise subjects
        subjects = []
        for doc in documents:
            if ("responses" in doc and
                "about_user" in doc["responses"] and
                    "study_field" in doc["responses"]["about_user"]):
                subject = doc["responses"]["about_user"]["study_field"]
                if subject:
                    subjects.append(subject)

        _, subject_clusters = self.cluster_similar_values(
            subjects, "subject")

        for subject, originals in subject_clusters.items():
            stats["subjects"][subject] = len(originals)

        # Detect course types from transcripts using regex
        course_patterns = {
            "A-levels": r'\b[aA][\s-]levels?\b|\b[aA] level\b',
            "BTECs": r'\bbtecs?\b|\bBTECs?\b',
            "Apprenticeships": r'\bapprenticeships?\b|\bApprenticeships?\b',
            "T-levels": r'\b[tT][\s-]levels?\b|\b[tT] level\b'
        }

        # Count course types
        for doc in documents:
            transcript = doc.get("transcript", "")
            if transcript:
                for course_type, pattern in course_patterns.items():
                    if re.search(pattern, transcript):
                        stats["course_types"][course_type] = stats["course_types"].get(
                            course_type, 0) + 1

        return stats

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
