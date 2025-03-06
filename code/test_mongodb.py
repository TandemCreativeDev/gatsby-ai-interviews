import streamlit as st
import datetime
from database import test_connection, get_mongo_client, get_collection

st.set_page_config(page_title="MongoDB Connection Test", page_icon="🔌")

st.title("MongoDB Connection Test")

# Test MongoDB connection
st.header("Connection Test")

if st.button("Test MongoDB Connection"):
    collections = test_connection()
    
    if collections:
        st.success(f"✅ Successfully connected to MongoDB!")
        st.write("Collections in the database:")
        for collection in collections:
            st.write(f"- {collection}")
    else:
        st.error("❌ Failed to connect to MongoDB. Please check your connection string in .streamlit/secrets.toml")

# Test inserting a document
st.header("Insert Test Document")

with st.form("insert_test"):
    test_name = st.text_input("Test Name", value=f"Test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    submit = st.form_submit_button("Insert Test Document")
    
    if submit:
        collection = get_collection()
        if collection is not None:
            try:
                result = collection.insert_one({
                    "test_name": test_name,
                    "timestamp": datetime.datetime.now(),
                    "test": True
                })
                
                if result.acknowledged:
                    st.success(f"✅ Successfully inserted test document with ID: {result.inserted_id}")
                else:
                    st.error("❌ Failed to insert test document")
            except Exception as e:
                st.error(f"❌ Error inserting test document: {e}")
        else:
            st.error("❌ Failed to get MongoDB collection")

# View recent test documents
st.header("Recent Test Documents")

if st.button("View Recent Test Documents"):
    collection = get_collection()
    if collection is not None:
        try:
            # Find test documents
            cursor = collection.find({"test": True}).sort("timestamp", -1).limit(5)
            documents = list(cursor)
            
            if len(documents) > 0:
                st.write(f"Found {len(documents)} test documents:")
                for doc in documents:
                    st.write(f"- {doc['test_name']} (ID: {doc['_id']}, Time: {doc['timestamp']})")
            else:
                st.info("No test documents found")
        except Exception as e:
            st.error(f"❌ Error retrieving test documents: {e}")
    else:
        st.error("❌ Failed to get MongoDB collection")

st.markdown("""
### Setup Instructions:
1. Make sure you have created a `.streamlit/secrets.toml` file with your MongoDB URI:
```toml
[mongo]
uri = "mongodb+srv://username:password@cluster.mongodb.net/AIinterview_database"
```
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```
""")
