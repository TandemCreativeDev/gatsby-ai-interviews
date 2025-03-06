import streamlit as st
from pymongo import MongoClient
import config
import datetime

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
        
        return client
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
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
        db = client[config.MONGODB_DB_NAME]
        return list(db.list_collection_names())
    return []

# Example function to save interview data to MongoDB
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
                "timestamp": datetime.datetime.now()
            }
            
            # Insert document
            result = collection.insert_one(document)
            
            return result.acknowledged
        return False
    except Exception as e:
        st.error(f"Failed to save interview data: {e}")
        return False
