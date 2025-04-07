import streamlit as st
import os
import sys
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

def setup_admin_page(title, logo_path=None):
    """Set up an admin page with login and standard layout
    
    Args:
        title (str): The title of the admin page
        logo_path (str, optional): Path to the logo. Defaults to config.LOGO_PATH.
    
    Returns:
        bool: True if logged in, False otherwise
    """
    # Set page configuration
    st.set_page_config(page_title=f"{title} | Gatsby AI Interview", page_icon=config.FAVICON_PATH)
    
    # Use the logo path from config if not specified
    if logo_path is None:
        logo_path = config.LOGO_PATH
    
    # Create login placeholder
    global login_placeholder
    login_placeholder = st.empty()
    
    # Create columns in the sidebar to center a smaller image
    col1, col2, col3 = st.sidebar.columns([1, 2, 1])
    with col2:
        # Display smaller centered image without pixelation by retaining aspect ratio
        st.image(logo_path, use_container_width=True)
    
    # Admin login - separate from regular login
    if not admin_login():
        st.stop()
        return False
    
    # Display page title
    st.title(title)
    
    return True