import json
import os
import time
import streamlit as st
from pymongo import MongoClient, ReturnDocument
import config
import datetime
import logging

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

def save_interview(username, transcript, time_data):
    """
    Save interview data to MongoDB
    
    Args:
        username (str): Username of the interviewee
        transcript (str): Interview transcript
        time_data (dict): Time-related data for the interview
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        collection = get_collection()
        if collection is not None:
            from pymongo import ReturnDocument
            # Create document with backup flag set to False (final save)
            document = {
                "username": username,
                "transcript": transcript,
                "time_data": time_data,
                "timestamp": datetime.datetime.now(),
                "metadata": {
                    "version": "1.0",
                    "source": "ai_interview_system"
                },
                "backup": False
            }
            
            if "mongo_doc_id" in st.session_state:
                filter_query = {"_id": st.session_state.mongo_doc_id}
            else:
                filter_query = {"username": username}
            
            updated_doc = collection.find_one_and_update(
                filter_query,
                {"$set": document},
                upsert=True,
                return_document=ReturnDocument.AFTER
            )
            
            if updated_doc:
                st.session_state.mongo_doc_id = updated_doc["_id"]
                logger.info(f"Successfully saved interview data for user: {username}")
                return True
            else:
                logger.warning(f"Failed to update interview data for user: {username}")
                _create_backup(username, {"username": username, "transcript": transcript, "time_data": time_data})
                return False
        else:
            logger.error("Failed to get MongoDB collection")
            _create_backup(username, {"username": username, "transcript": transcript, "time_data": time_data})
            return False
    except Exception as e:
        error_msg = f"Failed to save interview data: {e}"
        logger.error(error_msg)
        st.error(error_msg)
        _create_backup(username, {"username": username, "transcript": transcript, "time_data": time_data})
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
    from mongo_utils import save_interview_bulk
    for backup_path in backup_files:
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Attempt upload using save_interview_bulk
            success = save_interview_bulk(
                username=data.get("username", "unknown"),
                responses={},
                transcript=data.get("transcript", "")
            )
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

def _create_backup(username, data):
    """Helper function to create JSON backup"""
    try:
        # Make backup directory absolute 
        backup_dir = os.path.abspath(config.BACKUPS_DIRECTORY)
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create unique filename with timestamp
        filename = f"interview_{username}_{int(time.time())}.json"
        backup_path = os.path.join(backup_dir, filename)
        
        # Write data to file
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        print(f"Saved interview data to fallback JSON backup file: {backup_path}")
        return True
    except Exception as e:
        print(f"Failed to create backup file: {e}")
        
        # Try a fallback location in case the configured directory isn't accessible
        try:
            fallback_dir = "."  # Current directory
            backup_path = os.path.join(fallback_dir, filename)
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            print(f"Saved interview data to current directory: {backup_path}")
            return True
        except:
            print("Failed to create backup even in current directory")
            return False
