import json
import os
import streamlit as st
from pymongo import MongoClient
import config
import datetime
import logging

from summary_utils import generate_transcript_summary

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_mongo_client():
    """
    Get MongoDB client using connection string from Streamlit secrets
    """
    try:
        # Get MongoDB URI from Streamlit secrets
        mongo_uri = st.secrets["mongo"]["uri"]

        # Initialize MongoDB client
        client = MongoClient(mongo_uri)

        # Test connection
        client.admin.command('ping')
        logger.info("MongoDB connection successful")

        return client
    except Exception as e:
        error_msg = f"Failed to connect to MongoDB: {e}"
        logger.error(error_msg)
        st.error(error_msg)
        return None


def get_database():
    """
    Get MongoDB database
    """
    client = get_mongo_client()
    if client is not None:
        return client[config.MONGODB_DB_NAME]
    return None


def get_collection(type):
    """
    Get MongoDB collection
    """
    db = get_database()
    if db is not None:
        if type in config.MONGODB_COLLECTION_NAME:
            return db[config.MONGODB_COLLECTION_NAME[type]]
        else:
            logger.error(
                f"Collection type '{type}' not found in configuration.")
            return None
    return None


def test_connection():
    """
    Test MongoDB connection and return collection names
    """
    client = get_mongo_client()
    if client is not None:
        try:
            db = client[config.MONGODB_DB_NAME]
            collections = list(db.list_collection_names())
            logger.info(f"Found collections: {collections}")
            return collections
        except Exception as e:
            error_msg = f"Error listing collections: {e}"
            logger.error(error_msg)
            st.error(error_msg)
    return []


def prepare_mongo_data(
        username,
        transcript,
        time_data,
        college="",
        age_group="",
        gender="",
        backup=False
):
    """
    Prepare data for MongoDB

    Args:
        username (str): Username of the interviewee
        transcript (str): Interview transcript
        time_data (dict): Time-related data for the interview
        college (str, optional): Name of the college. Defaults to "".
        age_group (str, optional): Age group (Under 25 or 25 or older).
        gender (str, optional): Gender selection. Defaults to "".
        backup (bool, optional): Whether this is a backup. Defaults to False.

    Returns:
        dict: Mongo document
    """
    document = {
        "username": username,
        "completed": not backup,
        "backup": backup,
        "time_data": time_data,
        "college": college,
        "age_group": age_group,
        "gender": gender,
        "transcript": transcript,
        "timestamp": datetime.datetime.now(),
        "metadata": {
            "version": "1.0",
            "source": "ai_interview_system"
        }
    }
    if backup:
        document["transcript"] = transcript
    else:
        document.update(generate_transcript_summary(transcript))
    return document


def save_interview(document, type, update_if_exists=True):
    """
    Save interview data to MongoDB

    Args:
        document (dict): Interview data MongoDB document

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Convert timestamp from string back to datetime if needed
        if isinstance(document.get('timestamp'), str):
            try:
                document['timestamp'] = datetime.datetime.fromisoformat(
                    document['timestamp'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert timestamp to datetime: {e}")
                # If conversion fails, create a new timestamp
                document['timestamp'] = datetime.datetime.now()
        elif not isinstance(document.get('timestamp'), datetime.datetime):
            # If timestamp doesn't exist or isn't a datetime, create one
            document['timestamp'] = datetime.datetime.now()

        collection = get_collection(type)
        if collection is not None:
            from pymongo import ReturnDocument

            if "mongo_doc_id" in st.session_state:
                filter_query = {"_id": st.session_state.mongo_doc_id}
            else:
                filter_query = {"username": document['username']}

            updated_doc = collection.find_one_and_update(
                filter_query,
                {"$set": document},
                upsert=True,
                return_document=ReturnDocument.AFTER
            )

            if updated_doc:
                if update_if_exists:
                    st.session_state.mongo_doc_id = updated_doc["_id"]
                logger.info(
                    "Successfully saved interview data for user: "
                    f"{document['username']}"
                )
                return True
            else:
                logger.warning(
                    "Failed to update interview data for user: "
                    f"{document['username']}"
                )
                _create_backup(document)
                return False
        else:
            logger.error("Failed to get MongoDB collection")
            _create_backup(document)
            return False
    except Exception as e:
        error_msg = f"Failed to save interview data: {e}"
        logger.error(error_msg)
        st.error(error_msg)
        _create_backup(document)
        return False


def upload_local_backups(type="Student"):
    """
    Scan local backup directory for JSON backup files,
    attempt to upload them to MongoDB using save_interview_bulk,
    and delete the backup file if the upload is successful.
    """
    backup_dir = os.path.abspath(config.BACKUPS_DIRECTORY)
    import glob
    backup_files = glob.glob(os.path.join(backup_dir, "*.json"))
    if not backup_files:
        logger.info("No local backups to upload.")
        return
    for backup_path in backup_files:
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                document = json.load(f)
            # Attempt upload using save_interview_bulk
            success = save_interview(document, type)
            if success:
                os.remove(backup_path)
                logger.info(f"Uploaded and deleted backup file: {backup_path}")
            else:
                logger.error(f"Failed to upload backup file: {backup_path}")
        except Exception as e:
            logger.error(f"Error processing backup file {backup_path}: {e}")


def get_interviews(username=None, limit=100, type="Student", role=None):
    """
    Retrieve interview data from MongoDB

    Args:
        username (str, optional): Filter by username. Defaults to None.
        limit (int, optional): Maximum number of records to return. 
            Defaults to 100.
        type (str, optional): Type of interview ("Student" or "Staff").
            Defaults to "Student".
        role (str, optional): Filter staff interviews by role.
            Defaults to None.

    Returns:
        list: List of interview documents
    """
    try:
        collection = get_collection(type)
        if collection is not None:
            # Create filter
            filter_query = {}
            if username:
                filter_query["username"] = {
                    "$regex": f"^{username}", "$options": "i"}

            # Add role filter for Staff interviews
            if role and type == "Staff" and role != "All":
                filter_query["role"] = role

            # Query database
            cursor = collection.find(filter_query).sort(
                "timestamp", -1).limit(limit)

            # Convert cursor to list
            interviews = list(cursor)

            logger.info(f"Retrieved {len(interviews)} interviews from MongoDB")
            return interviews
        else:
            logger.error("Failed to get MongoDB collection")
            return []
    except Exception as e:
        error_msg = f"Failed to retrieve interview data: {e}"
        logger.error(error_msg)
        st.error(error_msg)
        return []


def get_staff_roles():
    """
    Retrieve unique staff roles from the database

    Returns:
        list: List of unique staff roles
    """
    try:
        collection = get_collection("Staff")
        if collection is not None:
            # Find unique roles in the staff collection
            roles = collection.distinct("role")

            # Add "All" option and sort
            all_roles = ["All"] + sorted(roles)

            logger.info(f"Retrieved {len(roles)} unique staff roles")
            return all_roles
        else:
            logger.error("Failed to get Staff collection")
            return ["All"]
    except Exception as e:
        error_msg = f"Failed to retrieve staff roles: {e}"
        logger.error(error_msg)
        return ["All"]


def delete_interview(interview_id, type):
    """
    Delete interview data from MongoDB by its _id.

    Args:
        interview_id: The _id of the interview document.

    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    try:
        collection = get_collection(type)
        if collection is not None:
            result = collection.delete_one({"_id": interview_id})
            if result.deleted_count == 1:
                logger.info(
                    f"Successfully deleted interview with id: {interview_id}")
                return True
            else:
                logger.warning(f"No document found with id: {interview_id}")
                return False
        else:
            logger.error("Failed to get MongoDB collection for deletion")
            return False
    except Exception as e:
        error_msg = f"Failed to delete interview data: {e}"
        logger.error(error_msg)
        return False


def reanalyse_transcript(interview_id, type="Student"):
    """
    Reanalyse the transcript of an interview and update the MongoDB document

    Args:
        interview_id: The _id of the interview document
        type: The type of transcript (Student or Staff)

    Returns:
        bool: True if reanalysis was successful, False otherwise
    """
    try:
        collection = get_collection(type)
        if collection is not None:
            # Get the interview document
            interview = collection.find_one({"_id": interview_id})
            if not interview:
                logger.warning(f"No interview found with id: {interview_id}")
                return False

            # Get the transcript
            transcript = interview.get("transcript")
            if not transcript:
                logger.warning(
                    "No transcript found for interview with id: "
                    f"{interview_id}")
                return False

            # Generate a new analysis based on type
            analysis = generate_transcript_summary(transcript, type)

            # Update the document in MongoDB
            result = collection.update_one(
                {"_id": interview_id},
                {"$set": analysis}
            )

            if result.modified_count == 1:
                logger.info(
                    f"Successfully reanalyzed {type} interview with id: "
                    f"{interview_id}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to update {type} "
                    f"interview with id: {interview_id}")
                return False
        else:
            logger.error(
                f"Failed to get MongoDB collection for {type} reanalysis")
            return False
    except Exception as e:
        error_msg = f"Failed to reanalyze {type} interview data: {e}"
        logger.error(error_msg)
        return False


def update_documents_with_normalised_data(documents, collection_type):
    """
    Update multiple documents in MongoDB with normalised data using a simpler approach
    with direct document updates one by one

    Args:
        documents (list): List of document objects with normalised data
        collection_type (str): Type of collection ("Student" or "Staff")

    Returns:
        tuple: (success_count, error_message)
    """
    # Configure logging to also write to a file for debugging
    import logging
    file_handler = logging.FileHandler('/tmp/mongodb_update.log')
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Also print to stdout for immediate visibility
    import sys
    print(f"Starting MongoDB update for {len(documents)} documents of type {collection_type}")
    
    try:
        collection = get_collection(collection_type)
        if collection is None:
            error_msg = f"Failed to get collection for type: {collection_type}"
            logger.error(error_msg)
            print(error_msg)
            return 0, error_msg
        
        # Test connection with reduced timeout
        try:
            print("Testing MongoDB connection...")
            import pymongo
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
            
            # Explicitly set a shorter server selection timeout
            client = collection.database.client
            client.admin.command('ismaster', serverSelectionTimeoutMS=5000)
            print("MongoDB connection test successful")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            error_msg = f"MongoDB connection test failed: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            return 0, error_msg
        
        print(f"Starting updates for {len(documents)} documents")
        logger.info(f"Starting updates for {len(documents)} documents")
        
        # Print first document for debugging
        if documents:
            first_doc = documents[0]
            print(f"First document: username={first_doc.get('username')}, fields={list(first_doc.keys())}")
        
        # Use a very small batch size to prevent timeouts
        success_count = 0
        error_count = 0
        batch_size = 5  # Very small batches
        timestamp = datetime.datetime.now()
        
        # Process in tiny batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            batch_msg = f"Processing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}"
            print(batch_msg)
            logger.info(batch_msg)
            
            # Process each document in batch
            for doc in batch:
                try:
                    # Get username - this is critical for our update
                    username = doc.get("username")
                    
                    if not username:
                        error_msg = f"Document missing username: {doc}"
                        print(error_msg)
                        logger.warning(error_msg)
                        error_count += 1
                        continue
                    
                    print(f"Updating document for username: {username}")
                    
                    # Create update fields
                    update_fields = {}
                    
                    # Add normalized fields that exist
                    if "college" in doc and doc["college"]:
                        update_fields["college"] = doc["college"]
                    
                    if "gender" in doc and doc["gender"]:
                        update_fields["gender"] = doc["gender"]
                    
                    if "age_group" in doc and doc["age_group"]:
                        update_fields["age_group"] = doc["age_group"]
                    
                    if "subjects" in doc:
                        update_fields["subjects"] = doc.get("subjects", [])
                    
                    if "course_types" in doc:
                        update_fields["course_types"] = doc.get("course_types", [])
                    
                    # Add timestamp
                    update_fields["normalised_at"] = timestamp
                    
                    # Directly update this document by username with write concern
                    result = collection.update_one(
                        {"username": username},
                        {"$set": update_fields},
                        upsert=False,  # Don't create if doesn't exist
                        bypass_document_validation=True  # Skip validation for speed
                    )
                    
                    # Check if update was successful
                    if result.modified_count == 1:
                        success_count += 1
                        print(f"Successfully updated document for: {username}")
                    else:
                        error_count += 1
                        print(f"No document found or no changes for username: {username}")
                
                except Exception as e:
                    error_count += 1
                    error_msg = f"Error updating document: {str(e)}"
                    print(error_msg)
                    logger.error(error_msg)
            
            # Log progress after each batch
            progress_msg = f"Progress: {i+len(batch)}/{len(documents)} documents processed. Successes: {success_count}, Errors: {error_count}"
            print(progress_msg)
            logger.info(progress_msg)
        
        # Final status
        final_msg = f"Completed updates: {success_count} successes, {error_count} errors"
        print(final_msg)
        logger.info(final_msg)
        
        if success_count == 0:
            return 0, f"No documents were updated. {error_count} errors occurred."
        elif error_count > 0:
            return success_count, f"Updated {success_count} documents with {error_count} errors."
        else:
            return success_count, None
        
    except Exception as e:
        error_msg = f"Failed to update documents with normalised data: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return 0, error_msg
    finally:
        # Remove file handler to avoid duplicate logging
        logger.removeHandler(file_handler)


def _create_backup(document):
    """Helper function to create JSON backup with proper datetime handling"""
    try:
        # Make backup directory absolute
        backup_dir = os.path.abspath(config.BACKUPS_DIRECTORY)
        os.makedirs(backup_dir, exist_ok=True)

        # Create unique filename with timestamp
        filename = f"interview_{document['username']}.json"
        backup_path = os.path.join(backup_dir, filename)

        # Create a copy of the document to avoid modifying the original
        json_document = document.copy()

        # Convert datetime to string format
        if isinstance(json_document['timestamp'], datetime.datetime):
            json_document['timestamp'] = json_document['timestamp'].isoformat()

        # Write data to file
        json_document['backup'] = True
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(json_document, f, indent=4)

        print(
            "Saved interview data to fallback JSON backup file: "
            f"{backup_path}")
        return True
    except Exception as e:
        print(f"Failed to create backup file: {e}")

        # Try a fallback location in case the
        # configured directory isn't accessible
        try:
            fallback_dir = "."  # Current directory
            backup_path = os.path.join(fallback_dir, filename)
            with open(backup_path, "w", encoding="utf-8") as f:
                # Using the already prepared json_document
                json.dump(json_document, f, indent=4)
            print(f"Saved interview data to current directory: {backup_path}")
            return True
        except Exception as e:
            print(f"Failed to create backup even in current directory: {e}")
            return False
