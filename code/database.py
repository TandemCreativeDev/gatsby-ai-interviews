import streamlit as st
from pymongo import MongoClient
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
    if client:
        return client[config.MONGODB_DB_NAME]
    return None

def get_collection():
    """
    Get MongoDB collection
    """
    db = get_database()
    if db:
        return db[config.MONGODB_COLLECTION_NAME]
    return None

def test_connection():
    """
    Test MongoDB connection and return collection names
    """
    client = get_mongo_client()
    if client:
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
        if collection:
            # Create document
            document = {
                "username": username,
                "transcript": transcript,
                "time_data": time_data,
                "timestamp": datetime.datetime.now(),
                "metadata": {
                    "version": "1.0",
                    "source": "ai_interview_system"
                }
            }
            
            # Insert document
            result = collection.insert_one(document)
            
            if result.acknowledged:
                logger.info(f"Successfully saved interview data for user: {username}")
                return True
            else:
                logger.warning(f"MongoDB acknowledged=False for user: {username}")
                return False
        else:
            logger.error("Failed to get MongoDB collection")
            return False
    except Exception as e:
        error_msg = f"Failed to save interview data: {e}"
        logger.error(error_msg)
        st.error(error_msg)
        return False

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
        if collection:
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
