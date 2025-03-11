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
        with login_placeholder.form("Admin Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
            
            if submitted:
                # Check if username is admin and password is correct
                if (username == config.ADMIN_USERNAME and 
                    username in st.secrets.get("passwords", {}) and 
                    password == st.secrets.passwords[username]):
                    st.session_state.admin_logged_in = True
                    login_placeholder.empty()
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
st.set_page_config(page_title="Admin View | Gatsby AI Interview", page_icon="🔒")
login_placeholder = st.empty()

# Admin login - separate from regular login
if not admin_login():
    st.stop()

# Admin view header
st.title("Interview Responses Admin View")
st.write("View completed interview transcripts")

def snake_to_title(s):
    """Convert snake_case to Title Case with spaces."""
    return " ".join(word.capitalize() for word in s.split("_"))

def render_dict_as_bullets(d, level=0):
    """Recursively renders dictionary contents as markdown bullet lists. Supports nested dicts and lists."""
    markdown_str = ""
    indent = "    " * level
    for k, v in d.items():
        title = snake_to_title(k)
        if isinstance(v, dict):
            markdown_str += f"{indent}- **{title}**:\n" + render_dict_as_bullets(v, level+1)
        elif isinstance(v, list):
            markdown_str += f"{indent}- **{title}**:\n"
            for item in v:
                if isinstance(item, dict):
                    markdown_str += render_dict_as_bullets(item, level+1)
                else:
                    markdown_str += f"{'    '*(level+1)}- {item}\n"
        else:
            markdown_str += f"{indent}- **{title}**: {v}\n"
    return markdown_str

if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

def delete_and_refresh(interview_id):
    from database import delete_interview
    if delete_interview(interview_id):
        st.success("Interview deleted successfully.")
    else:
        st.error("Failed to delete interview.")
    st.session_state.refresh_counter += 1

interview_container = st.container()

def render_interviews():
    with interview_container:
        try:
            from database import get_interviews, delete_interview
            interviews = get_interviews()
            if interviews:
                def safe_render_field(interview, key, label, render_type="text"):
                    try:
                        val = interview.get(key)
                        if val is not None:
                            if render_type == "text":
                                st.write(f"{label}: {val}")
                            elif render_type == "json":
                                st.json(val)
                    except Exception as e:
                        st.error(f"Error rendering {label}: {e}")
                for interview in interviews:
                    with st.expander(f"Interview with {interview.get('username', 'Unknown')} - {interview.get('timestamp', 'N/A')}", expanded=True):
                        st.text_area("Transcript", interview.get("transcript", ""), height=200)
                        for key, label in [("age_range", "Age Range"), ("gender", "Gender"), ("school", "School")]:
                            safe_render_field(interview, key, label, "text")
                        # Render formatted time and completion status
                        start_time = interview.get("start_time")
                        end_time = interview.get("end_time")
                        if start_time and end_time:
                            try:
                                from datetime import datetime
                                st_date = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                                date_str = st_date.strftime("%d %b %Y")
                                end_date = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%SZ")
                                duration = end_date - st_date
                                st.write(f"Date: {date_str}")
                                st.write(f"Duration: {duration}")
                            except Exception as e:
                                st.error(f"Error parsing time fields: {e}")
                        completed = interview.get("completed")
                        if completed is not None:
                            tick = "✓" if completed else "✗"
                            st.write(f"Completed: {tick}")
                        responses = interview.get("responses")
                        if responses and isinstance(responses, dict):
                            st.markdown("**Responses:**")
                            st.markdown(render_dict_as_bullets(responses))
                        sentiments = interview.get("sentiment_analysis")
                        if sentiments and isinstance(sentiments, dict):
                            st.markdown("**Sentiment Analysis:**")
                            st.markdown(render_dict_as_bullets(sentiments))
                        st.button("Delete", key=f"delete-{interview.get('_id')}", on_click=delete_and_refresh, args=(interview.get('_id'),))
                        st.download_button(
                            label="Download Transcript",
                            data=interview.get("transcript", ""),
                            file_name=f"{interview.get('username', 'unknown')}_transcript.txt",
                            mime="text/plain"
                        )
            else:
                st.info("No interview responses found in the database.")
        except Exception as e:
            st.error(f"Error fetching interview responses: {e}")

render_interviews()
