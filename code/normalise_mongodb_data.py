#!/usr/bin/env python3
"""
Script to normalize and update MongoDB documents with data from the normaliser.
Runs outside of Streamlit to avoid UI-related interruptions.
"""

from dashboard.student_data_normaliser import DataNormaliser
import config
import os
import sys
import logging
import datetime
from pymongo import MongoClient

# Add parent directory to path so we can import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'dashboard'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mongodb_normalisation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('normalise_mongodb')

# Import local modules


def get_mongo_client():
    """Get MongoDB client using connection string from a config file or env var"""
    try:
        # Try to get MongoDB URI from streamlit secrets or environment variable
        mongo_uri = "REDACTED"

        # Initialize MongoDB client
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)

        # Test connection
        client.admin.command('ping')
        logger.info("MongoDB connection successful")

        return client
    except ImportError:
        logger.error("Failed to import Streamlit - falling back to environment variable")
        # Handle the case where Streamlit is not available
        if 'MONGODB_URI' in os.environ:
            mongo_uri = os.environ['MONGODB_URI']
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
            client.admin.command('ping')
            logger.info("MongoDB connection successful (from env var)")
            return client
        else:
            logger.error("No MongoDB URI available")
            return None
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None


def get_database(client):
    """Get MongoDB database"""
    if client is not None:
        return client[config.MONGODB_DB_NAME]
    return None


def get_collection(db, collection_type="Student"):
    """Get MongoDB collection"""
    if db is not None:
        if collection_type in config.MONGODB_COLLECTION_NAME:
            collection_name = config.MONGODB_COLLECTION_NAME[collection_type]
            return db[collection_name]
        else:
            logger.error(f"Collection type '{collection_type}' not found in configuration.")
            return None
    return None


def get_documents(collection, limit=1000):
    """Retrieve documents from MongoDB collection"""
    try:
        logger.info(f"Fetching documents from MongoDB (limit: {limit})")
        documents = list(collection.find({}).limit(limit))
        logger.info(f"Retrieved {len(documents)} documents")
        return documents
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        return []


def normalise_documents(documents):
    """Process documents using the DataNormaliser class to normalize values"""
    try:
        logger.info(f"Starting normalization of {len(documents)} documents")
        normaliser = DataNormaliser()
        stats, docs_to_update = normaliser.generate_stats_with_normalised_values(documents)
        logger.info(f"Normalized {len(docs_to_update)} documents")

        # Log normalization stats
        logger.info(f"Number of colleges: {len(stats['college'])}")
        logger.info(f"Number of subjects: {len(stats['subjects'])}")

        return docs_to_update
    except Exception as e:
        logger.error(f"Error normalizing documents: {e}")
        return []


def update_documents(collection, documents):
    """Update MongoDB documents with normalized data"""
    success_count = 0
    error_count = 0
    batch_size = 10
    timestamp = datetime.datetime.now()

    logger.info(f"Starting to update {len(documents)} documents")

    # Process in batches to prevent timeouts
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")

        for doc in batch:
            try:
                # Get username
                username = doc.get("username")
                if not username:
                    logger.warning("Document missing username, skipping")
                    error_count += 1
                    continue

                # Create update fields
                update_fields = {
                    "college": doc.get("college"),
                    "gender": doc.get("gender"),
                    "age_group": doc.get("age_group"),
                    "subjects": doc.get("subjects", []),
                    "course_types": doc.get("course_types", []),
                    "normalised_at": timestamp
                }

                # Remove None values
                update_fields = {k: v for k, v in update_fields.items() if v is not None}

                # Update the document
                result = collection.update_one(
                    {"username": username},
                    {"$set": update_fields}
                )

                if result.modified_count == 1:
                    success_count += 1
                    logger.info(f"Updated document: {username}")
                else:
                    error_count += 1
                    logger.warning(f"Failed to update document: {username}")

            except Exception as e:
                error_count += 1
                logger.error(f"Error updating document: {e}")

        logger.info(f"Progress: {i+len(batch)}/{len(documents)}. Success: {success_count}, Errors: {error_count}")

    logger.info(f"Update complete. Success: {success_count}, Errors: {error_count}")
    return success_count, error_count


def main():
    """Main function to run the normalization and update process"""
    logger.info("Starting MongoDB document normalization")

    # Connect to MongoDB
    client = get_mongo_client()
    if not client:
        logger.error("Failed to connect to MongoDB. Exiting.")
        return

    # Get database and collection
    db = get_database(client)
    if db is None:
        logger.error("Failed to get database. Exiting.")
        return

    # Get collection (default: Student)
    collection_type = "Student"  # Change this to "Staff" if needed
    collection = get_collection(db, collection_type)
    if collection is None:
        logger.error(f"Failed to get {collection_type} collection. Exiting.")
        return

    # Fetch documents
    documents = get_documents(collection)
    if not documents:
        logger.error("No documents retrieved. Exiting.")
        return

    # Normalize documents
    logger.info("Normalizing documents...")
    docs_to_update = normalise_documents(documents)
    if not docs_to_update:
        logger.error("No documents to update after normalization. Exiting.")
        return

    # Update documents in MongoDB
    logger.info(f"Updating {len(docs_to_update)} documents...")
    success_count, error_count = update_documents(collection, docs_to_update)

    # Final summary
    logger.info("=" * 50)
    logger.info(f"SUMMARY: Updated {success_count} out of {len(docs_to_update)} documents")
    logger.info(f"Errors: {error_count}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
