import time
import random
from database import get_collection
import logging
from pymongo.errors import PyMongoError

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
    try:
        # Get MongoDB collection
        collection = get_collection()
        if collection is not None:
            # Create interview data document
            interview_data = {
                "user_id": username,
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "completed": True,
                "responses": responses,
                "full_transcript": transcript,
                "sentiment_analysis": {}
            }
            
            # Retry mechanism with exponential backoff
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    # Upsert document into MongoDB (overwrite existing document or insert new)
                    result = collection.update_one({"user_id": username}, {"$set": interview_data}, upsert=True)
                    
                    if result.acknowledged:
                        logger.info(f"Successfully saved bulk interview data for user: {username} (attempt {attempt+1})")
                        return True
                    else:
                        logger.warning(f"MongoDB acknowledged=False for user: {username} (attempt {attempt+1})")
                        
                        # If this is the last attempt, return False
                        if attempt == MAX_RETRY_ATTEMPTS - 1:
                            return False
                            
                except PyMongoError as e:
                    logger.error(f"MongoDB error on attempt {attempt+1}: {e}")
                    
                    # If this is the last attempt, return False
                    if attempt == MAX_RETRY_ATTEMPTS - 1:
                        logger.error(f"All {MAX_RETRY_ATTEMPTS} attempts failed. Giving up.")
                        return False
                        
                    # Calculate wait time with exponential backoff and jitter
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    logger.info(f"Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
            
            # This should not be reached, but just in case
            return False
        else:
            logger.error("Failed to get MongoDB collection")
            return False
    except Exception as e:
        error_msg = f"Failed to save interview data: {e}"
        logger.error(error_msg)
        return False
