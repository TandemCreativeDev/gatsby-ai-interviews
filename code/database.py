import json
import os
import time
import streamlit as st
from pymongo import MongoClient, ReturnDocument
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

def get_collection():
    """
    Get MongoDB collection
    """
    db = get_database()
    if db is not None:
        return db[config.MONGODB_COLLECTION_NAME]
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

def prepare_mongo_data(username, transcript, time_data, backup=False):
    """
    Prepare data for MongoDB
    
    Args:
        username (str): Username of the interviewee
        transcript (str): Interview transcript
        time_data (dict): Time-related data for the interview
    
    Returns:
        dict: Mongo document
    """
    document = {
                "username": username,
                "completed": not backup,
                "backup": backup,
                "time_data": time_data,
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

def save_interview(document):
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
                document['timestamp'] = datetime.datetime.fromisoformat(document['timestamp'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert timestamp to datetime: {e}")
                # If conversion fails, create a new timestamp
                document['timestamp'] = datetime.datetime.now()
        elif not isinstance(document.get('timestamp'), datetime.datetime):
            # If timestamp doesn't exist or isn't a datetime, create one
            document['timestamp'] = datetime.datetime.now()
            
        collection = get_collection()
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
                st.session_state.mongo_doc_id = updated_doc["_id"]
                logger.info(f"Successfully saved interview data for user: {document['username']}")
                return True
            else:
                logger.warning(f"Failed to update interview data for user: {document['username']}")
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

def upload_local_backups():
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
            success = save_interview(document)
            if success:
                os.remove(backup_path)
                logger.info(f"Uploaded and deleted backup file: {backup_path}")
            else:
                logger.error(f"Failed to upload backup file: {backup_path}")
        except Exception as e:
            logger.error(f"Error processing backup file {backup_path}: {e}")

def get_interviews(username=None, limit=100):
    """
    Retrieve interview data from MongoDB
    
    Args:
        username (str, optional): Filter by username. Defaults to None.
        limit (int, optional): Maximum number of records to return. Defaults to 100.
    
    Returns:
        list: List of interview documents
    """
    try:
        collection = get_collection()
        if collection is not None:
            # Create filter
            filter_query = {}
            if username:
                filter_query["username"] = {"$regex": f"^{username}", "$options": "i"}
            
            # Query database
            cursor = collection.find(filter_query).sort("timestamp", -1).limit(limit)
            
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
        
def delete_interview(interview_id):
    """
    Delete interview data from MongoDB by its _id.
    
    Args:
        interview_id: The _id of the interview document.
    
    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    try:
        collection = get_collection()
        if collection is not None:
            result = collection.delete_one({"_id": interview_id})
            if result.deleted_count == 1:
                logger.info(f"Successfully deleted interview with id: {interview_id}")
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

def reanalyse_transcript(interview_id):
    """
    Reanalyse the transcript of an interview and update the MongoDB document
    
    Args:
        interview_id: The _id of the interview document
        
    Returns:
        bool: True if reanalysis was successful, False otherwise
    """
    try:
        collection = get_collection()
        if collection is not None:
            # Get the interview document
            interview = collection.find_one({"_id": interview_id})
            if not interview:
                logger.warning(f"No interview found with id: {interview_id}")
                return False
                
            # Get the transcript
            transcript = interview.get("transcript")
            if not transcript:
                logger.warning(f"No transcript found for interview with id: {interview_id}")
                return False
                
            # Generate a new analysis
            analysis = generate_transcript_summary(transcript)
            
            # Update the document in MongoDB
            result = collection.update_one(
                {"_id": interview_id},
                {"$set": analysis}
            )
            
            if result.modified_count == 1:
                logger.info(f"Successfully reanalyzed interview with id: {interview_id}")
                return True
            else:
                logger.warning(f"Failed to update interview with id: {interview_id}")
                return False
        else:
            logger.error("Failed to get MongoDB collection for reanalysis")
            return False
    except Exception as e:
        error_msg = f"Failed to reanalyze interview data: {e}"
        logger.error(error_msg)
        return False

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
        
        print(f"Saved interview data to fallback JSON backup file: {backup_path}")
        return True
    except Exception as e:
        print(f"Failed to create backup file: {e}")
        
        # Try a fallback location in case the configured directory isn't accessible
        try:
            fallback_dir = "."  # Current directory
            backup_path = os.path.join(fallback_dir, filename)
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(json_document, f, indent=4)  # Using the already prepared json_document
            print(f"Saved interview data to current directory: {backup_path}")
            return True
        except Exception as e:
            print(f"Failed to create backup even in current directory: {e}")
            return False
