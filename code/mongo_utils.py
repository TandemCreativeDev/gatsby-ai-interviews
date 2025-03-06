import time
from database import get_collection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_interview_bulk(username, responses, transcript):
    """
    Save interview data to MongoDB in a structured format
    
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
            
            # Insert document into MongoDB
            result = collection.insert_one(interview_data)
            
            if result.acknowledged:
                logger.info(f"Successfully saved bulk interview data for user: {username}")
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
        return False
