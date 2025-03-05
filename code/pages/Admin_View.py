import streamlit as st
import os
import sys
import time

# Add parent directory to path so we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def admin_login():
    """Custom login just for admin page"""
    def login_form():
        with st.form("Admin Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
            
            if submitted:
                # Check if username is admin and password is correct
                if (username == config.ADMIN_USERNAME and 
                    username in st.secrets.get("passwords", {}) and 
                    password == st.secrets.passwords[username]):
                    st.session_state.admin_logged_in = True
                    return True
                else:
                    st.error("Invalid username or password")
                    return False
            return False
    
    # Check if already logged in
    if st.session_state.get("admin_logged_in", False):
        return True
        
    # Show login form
    return login_form()

def display_transcript(file_path):
    """Display a transcript file with formatting"""
    try:
        with open(file_path, "r") as f:
            transcript_text = f.read()
        
        # Display the transcript in a scrollable text area
        st.text_area("Interview Transcript", transcript_text, height=400)
    except Exception as e:
        st.error(f"Error reading transcript: {e}")

def display_time_info(file_path):
    """Display time information for an interview"""
    try:
        with open(file_path, "r") as f:
            time_info = f.read()
        
        st.info(time_info)
    except Exception as e:
        st.error(f"Error reading time information: {e}")

# Set page title and icon
st.set_page_config(page_title="Admin View", page_icon="🔒")

# Admin login - separate from regular login
if not admin_login():
    st.stop()

# Admin view header
st.title("Interview Responses Admin View")
st.write("View completed interview transcripts")

# Get list of completed interviews
transcript_files = []

st.write("### Debugging Information")
st.write(f"Current working directory: {os.getcwd()}")
st.write(f"Config BASE_DIR: {config.BASE_DIR}")
st.write(f"Config TRANSCRIPTS_DIRECTORY: {config.TRANSCRIPTS_DIRECTORY}")

try:
    # Ensure all data directories exist
    for dir_path in [config.TRANSCRIPTS_DIRECTORY, config.TIMES_DIRECTORY, config.BACKUPS_DIRECTORY]:
        if not os.path.exists(dir_path):
            st.warning(f"Directory doesn't exist, creating: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
        else:
            st.success(f"Directory exists: {dir_path}")
            
    st.write(f"BASE_DIR resolved to: {config.BASE_DIR}")
    
    # List files
    all_files = os.listdir(config.TRANSCRIPTS_DIRECTORY)
    st.write(f"Raw files in directory: {all_files}")
    
    transcript_files = [
        f for f in all_files 
        if os.path.isfile(os.path.join(config.TRANSCRIPTS_DIRECTORY, f))
    ]
    
    # Display all found files
    st.write(f"Found {len(transcript_files)} transcript files:")
    for file in transcript_files:
        st.write(f"- {file}")
    
except Exception as e:
    st.error(f"Error accessing transcripts directory: {e}")
    import traceback
    st.code(traceback.format_exc())

if not transcript_files:
    st.warning("No interview transcripts found.")
    st.stop()

# Extract display names from filenames
interview_names = []
for filename in transcript_files:
    name = filename.replace(".txt", "")
    
    # Skip non-timestamped files for testaccount (they'd be duplicates)
    if name == "testaccount":
        continue
        
    # Format display name to be more user-friendly
    if "_20" in name:  # Has timestamp
        username, timestamp = name.split("_", 1)
        # Format timestamp for display - "2025_03_05_10_12_19" to "2025/03/05---10:12_19"
        parts = timestamp.split("_", 5)
        if len(parts) >= 6:
            year, month, day, hour, minute, second = parts[:6]
            formatted_time = f"{year}/{month}/{day}---{hour}:{minute}_{second}"
            display_name = f"{username} ({formatted_time})"
            interview_names.append({"display": display_name, "filename": name})
        else:
            interview_names.append({"display": name, "filename": name})
    else:
        # For non-timestamped files (except testaccount which was skipped)
        interview_names.append({"display": name, "filename": name})

# Sort by timestamp (newest first)
interview_names.sort(key=lambda x: x["filename"], reverse=True)

# Create a dropdown to select which interview to view
selected_interview = st.selectbox(
    "Select an interview to view:", 
    [interview["display"] for interview in interview_names]
)

if selected_interview:
    # Find the filename that matches the selected display name
    selected_filename = next(
        interview["filename"] for interview in interview_names 
        if interview["display"] == selected_interview
    )
    
    transcript_path = os.path.join(config.TRANSCRIPTS_DIRECTORY, f"{selected_filename}.txt")
    time_path = os.path.join(config.TIMES_DIRECTORY, f"{selected_filename}.txt")
    
    # Display interview metadata
    display_username = selected_interview.split(" (")[0] if " (" in selected_interview else selected_interview
    st.subheader(f"Interview with {display_username}")
    
    # Display time information if available
    if os.path.exists(time_path):
        display_time_info(time_path)
    
    # Display the transcript
    display_transcript(transcript_path)
    
    # Option to download the transcript
    with open(transcript_path, "r") as f:
        transcript_text = f.read()
        
    st.download_button(
        label="Download Transcript",
        data=transcript_text,
        file_name=f"{selected_filename}_transcript.txt",
        mime="text/plain"
    )