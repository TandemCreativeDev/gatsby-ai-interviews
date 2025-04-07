import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd
import config  # Import the config module for MongoDB settings

# Import login functionality from the centralized login module
from login import setup_admin_page

# Initialize the admin page with login
if not setup_admin_page("Transfer Transcripts | Gatsby AI Interview"):
    st.stop()

st.write("Transfer documents between MongoDB collections based on timestamp criteria.")

st.header("Manual Transcript Transfer")

# Initialize session state for extracted documents
if 'extracted_docs' not in st.session_state:
    st.session_state.extracted_docs = None
if 'extraction_count' not in st.session_state:
    st.session_state.extraction_count = 0
if 'extraction_complete' not in st.session_state:
    st.session_state.extraction_complete = False
if 'selected_docs' not in st.session_state:
    st.session_state.selected_docs = {}
if 'select_all' not in st.session_state:
    st.session_state.select_all = True
if 'need_update_select_all' not in st.session_state:
    st.session_state.need_update_select_all = False
if 'reset_complete' not in st.session_state:
    st.session_state.reset_complete = False

# Handle the reset if needed (from a previous insertion)
if st.session_state.reset_complete:
    st.session_state.select_all = True
    st.session_state.reset_complete = False

# Get MongoDB connection details from secrets
try:
    mongo_uri = st.secrets["mongo"]["uri"]
except Exception:
    # Fallback for local development or if secrets are not configured
    mongo_uri = "mongodb://localhost:27017/"
    st.sidebar.warning("Using default MongoDB connection. For production, set up secrets.toml.")

# MongoDB database name from config
database_name = config.MONGODB_DB_NAME

# MongoDB connection settings
with st.sidebar:
    st.header("Database Connection")
    # Display the connection string but don't allow editing if from secrets
    if "mongo" in st.secrets:
        st.text_input("MongoDB URI (from secrets)", value="[Connected using secrets.toml]", disabled=True)
    else:
        mongo_uri = st.text_input("MongoDB URI", value=mongo_uri, type="password")
    
    st.text_input("Database Name (from config)", value=database_name, disabled=True)
    st.info("Make sure your MongoDB instance is running and accessible.")

# Function to connect to MongoDB
def connect_to_mongodb(uri, db_name):
    try:
        client = MongoClient(uri)
        # Test the connection by issuing a server info command
        client.admin.command('ismaster')
        db = client[db_name]
        return client, db
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None, None

# Function to extract documents
def extract_documents(db, collection_name, query):
    try:
        collection = db[collection_name]
        documents = list(collection.find(query))
        
        if not documents:
            st.info(f"No documents found in {collection_name} matching the query.")
            return None, 0
        
        return documents, len(documents)
    except Exception as e:
        st.error(f"Error extracting documents: {e}")
        return None, 0

# Function to insert documents
def insert_documents(db, dest_name, documents):
    try:
        destination = db[dest_name]
        
        if not documents:
            st.warning("No documents to insert.")
            return 0
        
        doc_count = len(documents)
        
        # Progress bar for insertion
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process each document
        inserted_count = 0
        for i, document in enumerate(documents):
            # Remove the _id field to avoid duplication issues
            if '_id' in document:
                document_id = document['_id']
                document_copy = document.copy()
                document_copy.pop('_id')
            else:
                document_id = None
                document_copy = document
                
            # Insert into destination collection
            result = destination.insert_one(document_copy)
            inserted_count += 1
            
            # Update progress
            progress = int((i + 1) / doc_count * 100)
            progress_bar.progress(progress)
            status_text.text(f"Inserted {i+1}/{doc_count} documents ({progress}%)")
        
        return inserted_count
    except Exception as e:
        st.error(f"Error during insertion: {e}")
        return 0

# Collection input
col1, col2 = st.columns(2)

with col1:
    source_collection = st.text_input("Source Collection", value="responses")

with col2:
    destination_collection = st.text_input("Destination Collection", value="students")

# Date range input
st.subheader("Timestamp Range")
date_col1, date_col2 = st.columns(2)

with date_col1:
    start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=1))
    start_time = st.time_input("Start Time", value=datetime.strptime("00:00:00", "%H:%M:%S").time())

with date_col2:
    end_date = st.date_input("End Date", value=datetime.now())
    end_time = st.time_input("End Time", value=datetime.strptime("23:59:59", "%H:%M:%S").time())

# Timestamp field
timestamp_field = st.text_input("Timestamp Field Name", value="timestamp")

# Create datetime objects from inputs
start_datetime = datetime.combine(start_date, start_time)
end_datetime = datetime.combine(end_date, end_time)

# Display the selected range
st.write(f"Selected time range: {start_datetime} to {end_datetime}")

# Step 1: Extract button
if st.button("Extract Documents for Review"):
    # Connect to MongoDB
    client, db = connect_to_mongodb(mongo_uri, database_name)
    
    if client is not None and db is not None:
        # Build the query
        query = {
            timestamp_field: {
                "$gte": start_datetime,
                "$lte": end_datetime
            }
        }
        
        st.subheader("Query Preview")
        st.code(f"""
        {{
            "{timestamp_field}": {{
                "$gte": "{start_datetime.isoformat()}",
                "$lte": "{end_datetime.isoformat()}"
            }}
        }}
        """)
        
        # Extract documents
        with st.spinner("Extracting documents..."):
            docs, count = extract_documents(db, source_collection, query)
            
        if docs:
            st.session_state.extracted_docs = docs
            st.session_state.extraction_count = count
            st.session_state.extraction_complete = True
            
            # Initialize all documents as selected
            st.session_state.selected_docs = {str(doc.get('_id', i)): True for i, doc in enumerate(docs)}
            st.session_state.select_all = True
            
            st.success(f"Successfully extracted {count} documents from '{source_collection}'")
        else:
            st.session_state.extraction_complete = False
        
        # Close the MongoDB connection
        client.close()
        
        # Force a rerun to update the UI
        st.rerun()

# Step 2: Review and Insert (only shown if extraction is complete)
if st.session_state.extraction_complete:
    st.subheader(f"Review Extracted Documents ({st.session_state.extraction_count})")
    
    # Function to handle individual checkbox changes
    def on_checkbox_change(doc_id):
        # Update the selected_docs dictionary
        st.session_state.selected_docs[doc_id] = st.session_state[f"doc_{doc_id}"]
        # Mark that we need to update the select_all state
        st.session_state.need_update_select_all = True
    
    # Select/Deselect all checkbox
    def toggle_all():
        new_state = st.session_state.select_all
        for doc_id in st.session_state.selected_docs:
            st.session_state.selected_docs[doc_id] = new_state
            st.session_state[f"doc_{doc_id}"] = new_state  # Update the checkbox widget state
    
    # Check if we need to update the select_all state
    if st.session_state.need_update_select_all:
        all_selected = all(st.session_state.selected_docs.values())
        st.session_state.select_all = all_selected
        st.session_state.need_update_select_all = False
    
    select_all = st.checkbox("Select/Deselect All", value=st.session_state.select_all, key="select_all", on_change=toggle_all)
    
    # Convert MongoDB documents to a readable format with checkboxes
    review_data = []
    
    # Create a container for the checkboxes and data
    doc_container = st.container()
    
    with doc_container:
        for i, doc in enumerate(st.session_state.extracted_docs):
            doc_id = str(doc.get('_id', i))
            
            # Create a row with checkbox and document data
            col1, col2, col3, col4 = st.columns([0.5, 1.5, 2, 2])
            
            with col1:
                # Create the checkbox
                doc_selected = st.checkbox(
                    f"###", 
                    value=st.session_state.selected_docs.get(doc_id, True),
                    key=f"doc_{doc_id}",
                    label_visibility="collapsed",
                    on_change=lambda: on_checkbox_change(doc_id)
                )
                st.session_state.selected_docs[doc_id] = doc_selected
            
            with col2:
                st.text(doc_id[:8] + "..." if len(doc_id) > 10 else doc_id)
            
            with col3:
                st.text(doc.get('username', 'N/A'))
            
            with col4:
                timestamp_value = doc.get(timestamp_field, 'N/A')
                if isinstance(timestamp_value, datetime):
                    st.text(timestamp_value.strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    st.text(str(timestamp_value))
            
            # Add a horizontal separator
            st.markdown("---")
    
    # Add details expander for full document inspection - only show selected documents
    with st.expander("View Selected Documents Details"):
        # Get list of selected documents
        selected_docs_list = [
            doc for i, doc in enumerate(st.session_state.extracted_docs)
            if st.session_state.selected_docs.get(str(doc.get('_id', i)), False)
        ]
        
        if not selected_docs_list:
            st.info("No documents currently selected for inspection.")
        else:
            st.write(f"Showing details for {len(selected_docs_list)} selected document(s):")
            
            # Create tabs for each selected document
            if len(selected_docs_list) > 1:
                tabs = st.tabs([f"Doc {i+1}" for i in range(len(selected_docs_list))])
                for i, (tab, doc) in enumerate(zip(tabs, selected_docs_list)):
                    with tab:
                        st.write(f"**Document ID:** {doc.get('_id', 'N/A')}")
                        st.write(f"**Username:** {doc.get('username', 'N/A')}")
                        st.json(doc)
            else:
                # Just display the one document without tabs
                doc = selected_docs_list[0]
                st.write(f"**Document ID:** {doc.get('_id', 'N/A')}")
                st.write(f"**Username:** {doc.get('username', 'N/A')}")
                st.json(doc)
    
    # Count selected documents
    selected_count = sum(1 for selected in st.session_state.selected_docs.values() if selected)
    
    # Step 3: Insert button
    if st.button(f"Insert Selected Documents ({selected_count})"):
        # Connect to MongoDB again
        client, db = connect_to_mongodb(mongo_uri, database_name)
        
        if client is not None and db is not None:
            st.subheader("Insertion Results")
            
            # Filter only the selected documents
            selected_docs = [
                doc for i, doc in enumerate(st.session_state.extracted_docs)
                if st.session_state.selected_docs.get(str(doc.get('_id', i)), False)
            ]
            
            if not selected_docs:
                st.warning("No documents selected for insertion.")
            else:
                # Insert selected documents
                with st.spinner(f"Inserting {len(selected_docs)} documents..."):
                    inserted = insert_documents(db, destination_collection, selected_docs)
                
                if inserted > 0:
                    st.success(f"Successfully inserted {inserted} documents into '{destination_collection}'")
                    
                    # Reset extraction state to start fresh
                    # Instead of directly setting select_all which causes an error,
                    # we'll use a flag to trigger a full reset on next page load
                    st.session_state.extraction_complete = False
                    st.session_state.extracted_docs = None
                    st.session_state.extraction_count = 0
                    st.session_state.selected_docs = {}
                    # Set a flag to indicate we should reset on next load
                    st.session_state.reset_complete = True
                    
                    # Use a button to continue
                    st.button("Start New Transfer", on_click=lambda: st.rerun())
            
            # Close the MongoDB connection
            client.close()