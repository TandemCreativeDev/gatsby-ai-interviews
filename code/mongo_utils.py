import time
import random
import streamlit as st

from database import get_collection
import logging
from pymongo.errors import PyMongoError
import json
import os

import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration for retry mechanism
MAX_RETRY_ATTEMPTS = 3

def save_interview_bulk(username, responses, transcript):
    """
    Save interview data to MongoDB in a structured format with retry mechanism
    
    Args:
        username (str): Username of the interviewee
        responses (dict): Dictionary containing structured responses
        transcript (str): Full interview transcript
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Create interview data document once
    interview_data = {
        "user_id": username,
        "backup": True,
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "completed": True,
        "responses": responses,
        "full_transcript": transcript,
        "sentiment_analysis": {}
    }

    try:
        # Get MongoDB collection
        collection = get_collection()
        if collection is None:
            logger.error("Failed to get MongoDB collection")
            # Create backup before returning
            return create_backup(username, interview_data)
        
        # Determine filter query: use stored _id if available; otherwise, fall back to user_id.
        if "mongo_doc_id" in st.session_state:
            filter_query = {"_id": st.session_state.mongo_doc_id}
        else:
            filter_query = {"user_id": username}
        
        # Retry mechanism with exponential backoff
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                from pymongo import ReturnDocument
                updated_doc = collection.find_one_and_update(
                    filter_query,
                    {"$set": interview_data},
                    upsert=True,
                    return_document=ReturnDocument.AFTER
                )
                
                if updated_doc:
                    st.session_state.mongo_doc_id = updated_doc["_id"]
                    logger.info(f"Successfully saved bulk interview data for user: {username} (attempt {attempt+1})")
                    return True
                else:
                    logger.warning(f"MongoDB acknowledged=False for user: {username} (attempt {attempt+1})")
                    
                    # If this is the last attempt, break to trigger backup
                    if attempt == MAX_RETRY_ATTEMPTS - 1:
                        break
                        
            except PyMongoError as e:
                logger.error(f"MongoDB error on attempt {attempt+1}: {e}")
                
                # If this is the last attempt, break to trigger backup
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    logger.error(f"All {MAX_RETRY_ATTEMPTS} attempts failed. Giving up.")
                    break
                    
                # Calculate wait time with exponential backoff and jitter
                wait_time = 2 ** attempt + random.uniform(0, 1)
                logger.info(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        # If we get here, all database attempts failed
        logger.error(f"All {MAX_RETRY_ATTEMPTS} attempts failed. Falling back to JSON backup.")
        return create_backup(username, interview_data)
    
    except Exception as e:
        error_msg = f"Failed to save interview data: {e}"
        logger.error(error_msg)
        # Create backup even in case of unexpected exceptions
        return create_backup(username, interview_data)

def create_backup(username, interview_data):
    """Helper function to create JSON backup"""
    try:
        backup_dir = config.BACKUPS_DIRECTORY
        # Ensure directory exists with full path
        os.makedirs(os.path.abspath(backup_dir), exist_ok=True)
        filename = f"interview_{username}_{int(time.time())}.json"
        backup_path = os.path.join(backup_dir, filename)
        
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(interview_data, f, indent=4)
        
        logger.info(f"Saved interview data to fallback JSON backup file: {backup_path}")
        return False  # Still return False as the primary operation failed
    except Exception as e:
        logger.error(f"Failed to create backup file: {e}")
        return False
