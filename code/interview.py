
import streamlit as st
import time
from database import prepare_mongo_data, save_interview, test_connection, upload_local_backups
import os
import config

# Load API library
if "gpt" in config.MODEL["chat"].lower():
    api = "openai"
    from openai import OpenAI

elif "claude" in config.MODEL["chat"].lower():
    api = "anthropic"
    import anthropic
else:
    raise ValueError(
        "Model does not contain 'gpt' or 'claude'; unable to determine API."
    )

# Set page title and icon
st.set_page_config(page_title="Interview | Gatsby AI Interview", page_icon=config.FAVICON_PATH)

# Create columns in the sidebar to center a smaller image
col1, col2, col3 = st.sidebar.columns([1, 2, 1])
with col2:
    # Display smaller centered image without pixelation by retaining aspect ratio
    st.image(config.LOGO_PATH, use_container_width=True)

# Create directories if they do not already exist
if not os.path.exists(config.BACKUPS_DIRECTORY):
    os.makedirs(config.BACKUPS_DIRECTORY)
upload_local_backups("Student")


# Initialise session state
if "interview_active" not in st.session_state:
    st.session_state.interview_active = True

# Initialise messages list in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Store start time in session state
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()
    st.session_state.start_time_file_names = time.strftime(
        "%Y_%m_%d_%H_%M_%S", time.localtime(st.session_state.start_time)
    )
    
# Initialize user input fields
if "user_info_submitted" not in st.session_state:
    st.session_state.user_info_submitted = False

if "college" not in st.session_state:
    st.session_state.college = ""
    
if "age_group" not in st.session_state:
    st.session_state.age_group = ""
    
if "gender" not in st.session_state:
    st.session_state.gender = ""

# # Check if interview previously completed by querying the database
# interviews = get_interviews(username=st.session_state.username)
# interview_previously_completed = len(interviews) > 0

# # If app started but interview was previously completed
# if interview_previously_completed and not st.session_state.messages:

#     st.session_state.interview_active = False
#     completed_message = "Interview already completed."
#     st.markdown(completed_message)

# Add 'Quit' button to dashboard
col1, col2 = st.columns([0.85, 0.15])
# Place where the second column is
with col2:

    # If interview is active and 'Quit' button is clicked
    if st.session_state.interview_active and st.button(
        "Quit", help="End the interview."
    ):

        # Set interview to inactive, display quit message, and store data
        st.session_state.interview_active = False
        quit_message = "You have cancelled the interview."
        st.session_state.messages.append({"role": "assistant", "content": quit_message})
        
        # Use timestamped username to avoid overwriting previous interviews
        timestamped_username = f"{st.session_state.username}_{st.session_state.start_time_file_names}"
        
        
        # Save to MongoDB
        try:
            with st.spinner("Saving interview data. Please wait and do not close this page..."):
                # Get transcript and time data
                transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages if msg['role'] != "system"])
                time_data = {
                    "start_time": st.session_state.start_time,
                    "end_time": time.time(),
                    "duration": time.time() - st.session_state.start_time,
                    "status": "quit"
                }
                
                # Save to MongoDB
                document = prepare_mongo_data(
                    username=timestamped_username,
                    transcript=transcript,
                    time_data=time_data,
                    college=st.session_state.college,
                    age_group=st.session_state.age_group,
                    gender=st.session_state.gender
                )
                save_interview(document, "Student")
                # If MongoDB connection is restored, delete backup file
                if test_connection():
                    backup_file = os.path.join(config.BACKUPS_DIRECTORY, f"{timestamped_username}.json")
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                        st.sidebar.info("Backup deleted after successful MongoDB save.")
        except Exception as e:
            st.sidebar.error(f"Failed to save to MongoDB: {e}")


# Upon rerun, display the previous conversation (except system prompt or first message)
# Only show messages if user info has been submitted
if st.session_state.user_info_submitted:
    for message in st.session_state.messages[1:]:
        if message["role"] == "assistant":
            avatar = config.AVATAR_INTERVIEWER
        else:
            avatar = config.AVATAR_RESPONDENT
        # Only display messages without codes
        if not any(code in message["content"] for code in config.CLOSING_MESSAGES.keys()):
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

# Load API client
if api == "openai":
    client = OpenAI(api_key=st.secrets["API_KEY_OPENAI"])
    api_kwargs = {"stream": True}
elif api == "anthropic":
    client = anthropic.Anthropic(api_key=st.secrets["API_KEY_ANTHROPIC"])
    api_kwargs = {"system": config.SYSTEM_PROMPT}

# API kwargs
api_kwargs["messages"] = st.session_state.messages
api_kwargs["model"] = config.MODEL["chat"]
api_kwargs["max_tokens"] = config.MAX_OUTPUT_TOKENS
if config.TEMPERATURE is not None:
    api_kwargs["temperature"] = config.TEMPERATURE

# In case the interview history is still empty, pass system prompt to model, and
# generate and display its first message - but only if user info has been submitted
if not st.session_state.messages and st.session_state.user_info_submitted:

    if api == "openai":

        st.session_state.messages.append(
            {"role": "system", "content": config.SYSTEM_PROMPT}
        )
        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            try:
                stream = client.chat.completions.create(**api_kwargs)
                message_interviewer = st.write_stream(stream)
            except Exception as e:
                st.error("We are currently experiencing technical issues, please try again later")
                st.info("Please inform the study coordinator about this issue")
                # Log the error without displaying traceback in UI
                print(f"OpenAI API error: {str(e)}")  # This will be logged in the console only
                message_interviewer = "I apologize, but we're having trouble connecting right now. Please try again later."
                st.markdown(message_interviewer)

    elif api == "anthropic":

        st.session_state.messages.append({"role": "user", "content": "Hi"})
        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            message_placeholder = st.empty()
            message_interviewer = ""
            try:
                with client.messages.stream(**api_kwargs) as stream:
                    for text_delta in stream.text_stream:
                        if text_delta != None:
                            message_interviewer += text_delta
                        message_placeholder.markdown(message_interviewer + "▌")
                message_placeholder.markdown(message_interviewer)
            except Exception as e:
                st.error("We are currently experiencing technical issues, please try again later")
                st.info("Please inform the study coordinator about this issue")
                # Log the error without displaying traceback in UI
                print(f"Anthropic API error: {str(e)}")  # This will be logged in the console only
                message_interviewer = "I apologize, but we're having trouble connecting right now. Please try again later."
                message_placeholder.markdown(message_interviewer)

    st.session_state.messages.append(
        {"role": "assistant", "content": message_interviewer}
    )



# Display user information form if not yet submitted
if st.session_state.interview_active and not st.session_state.user_info_submitted:
    st.markdown("### Before we start, please provide the following information:")
    
    with st.form("user_info_form"):
        college = st.text_input("College Name", value=st.session_state.college)
        age_group = st.selectbox("Age Group", options=["", "Under 25", "25 or older"], index=0)
        gender = st.selectbox("Gender", options=["", "Male", "Female", "Non-binary", "Prefer not to say"], index=0)
        
        submit_button = st.form_submit_button("Start Interview")
        
        if submit_button:
            if not college:
                st.error("Please enter your college name.")
            elif not age_group:
                st.error("Please select your age group.")
            elif not gender:
                st.error("Please select your gender.")
            else:
                st.session_state.college = college
                st.session_state.age_group = age_group
                st.session_state.gender = gender
                st.session_state.user_info_submitted = True
                st.rerun()

# Main chat if interview is active and user info has been submitted
elif st.session_state.interview_active and st.session_state.user_info_submitted:

    # Chat input and message for respondent
    if message_respondent := st.chat_input("Your message here"):
        st.session_state.messages.append(
            {"role": "user", "content": message_respondent}
        )

        # Display respondent message
        with st.chat_message("user", avatar=config.AVATAR_RESPONDENT):
            st.markdown(message_respondent)

        # Generate and display interviewer message
        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):

            # Create placeholder for message in chat interface
            message_placeholder = st.empty()

            # Initialise message of interviewer
            message_interviewer = ""

            if api == "openai":

                # Stream responses
                try:
                    stream = client.chat.completions.create(**api_kwargs)

                    for message in stream:
                        text_delta = message.choices[0].delta.content
                        if text_delta != None:
                            message_interviewer += text_delta
                        # Start displaying message only after 5 characters to first check for codes
                        if len(message_interviewer) > 5:
                            message_placeholder.markdown(message_interviewer + "▌")
                        if any(
                            code in message_interviewer
                            for code in config.CLOSING_MESSAGES.keys()
                        ):
                            # Stop displaying the progress of the message in case of a code
                            message_placeholder.empty()
                            break
                except Exception as e:
                    st.error("We are currently experiencing technical issues, please try again later")
                    st.info("Please inform the study coordinator about this issue")
                    # Log the error without displaying traceback in UI
                    print(f"OpenAI API error: {str(e)}")  # This will be logged in the console only
                    message_interviewer = "I apologize, but we're having trouble connecting right now. Please try again later."

            elif api == "anthropic":

                # Stream responses
                try:
                    with client.messages.stream(**api_kwargs) as stream:
                        for text_delta in stream.text_stream:
                            if text_delta != None:
                                message_interviewer += text_delta
                            # Start displaying message only after 5 characters to first check for codes
                            if len(message_interviewer) > 5:
                                message_placeholder.markdown(message_interviewer + "▌")
                            if any(
                                code in message_interviewer
                                for code in config.CLOSING_MESSAGES.keys()
                            ):
                                # Stop displaying the progress of the message in case of a code
                                message_placeholder.empty()
                                break
                except Exception as e:
                    st.error("We are currently experiencing technical issues, please try again later")
                    st.info("Please inform the study coordinator about this issue")
                    # Log the error without displaying traceback in UI
                    print(f"Anthropic API error: {str(e)}")  # This will be logged in the console only
                    message_interviewer = "I apologize, but we're having trouble connecting right now. Please try again later."

            # If no code is in the message, display and store the message
            if not any(
                code in message_interviewer for code in config.CLOSING_MESSAGES.keys()
            ):

                message_placeholder.markdown(message_interviewer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": message_interviewer}
                )

                # Regularly save interview progress to MongoDB (as backup)
                try:
                    transcript = "\n".join([f"{msg['role']}: {msg['content']}" 
                                             for msg in st.session_state.messages if msg['role'] != "system"])
                    time_data = {
                        "start_time": st.session_state.start_time,
                        "current_time": time.time(),
                        "duration_so_far": time.time() - st.session_state.start_time,
                        "status": "in_progress"
                    }
                    document = prepare_mongo_data(
                        username=f"{st.session_state.username}_backup_{st.session_state.start_time_file_names}",
                        transcript=transcript,
                        time_data=time_data,
                        college=st.session_state.college,
                        age_group=st.session_state.age_group,
                        gender=st.session_state.gender,
                        backup=True
                    )
                    save_interview(document, "Student")
                except:
                    pass

            # If code in the message, display the associated closing message instead
            # Loop over all codes
            for code in config.CLOSING_MESSAGES.keys():

                if code in message_interviewer:
                    # Store message in list of messages
                    st.session_state.messages.append(
                        {"role": "assistant", "content": message_interviewer}
                    )

                    # Set chat to inactive and display closing message
                    st.session_state.interview_active = False
                    closing_message = config.CLOSING_MESSAGES[code]
                    st.markdown(closing_message)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": closing_message}
                    )

                    # Store final transcript and time directly to MongoDB
                    timestamped_username = f"{st.session_state.username}_{st.session_state.start_time_file_names}"
                    try:
                        with st.spinner("Saving interview data. Please wait and do not close this page..."):
                            transcript = "\n".join([f"{msg['role']}: {msg['content']}" 
                                                for msg in st.session_state.messages if msg['role'] != "system"])
                            time_data = {
                                "start_time": st.session_state.start_time,
                                "end_time": time.time(),
                                "duration": time.time() - st.session_state.start_time
                            }
                            document = prepare_mongo_data(
                                username=timestamped_username,
                                transcript=transcript,
                                time_data=time_data,
                                college=st.session_state.college,
                                age_group=st.session_state.age_group,
                                gender=st.session_state.gender
                            )
                            success = save_interview(document, "Student")
                            if success:
                                st.success("✅ Interview saved, you may now close this page.")
                            else:
                                st.error("❌ Interview save failed: temporary backup saved locally")
                    except Exception as e:
                        st.sidebar.error(f"Failed to save to MongoDB: {e}")
