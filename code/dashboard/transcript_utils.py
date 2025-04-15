import streamlit as st
from database import delete_interview, reanalyse_transcript, get_interviews
from datetime import datetime, timedelta


def snake_to_title(s):
    """Convert snake_case to Title Case with spaces."""
    return " ".join(word.capitalize() for word in s.split("_"))


def render_dict_as_bullets(d, level=0):
    """
    Recursively renders dictionary contents as markdown bullet lists.
    Supports nested dicts and lists.
    """
    markdown_str = ""
    indent = "    " * level
    for k, v in d.items():
        title = snake_to_title(k)
        if isinstance(v, dict):
            markdown_str += f"{indent}- **{title}**:\n" + \
                render_dict_as_bullets(v, level+1)
        elif isinstance(v, list):
            markdown_str += f"{indent}- **{title}**:\n"
            for item in v:
                if isinstance(item, dict):
                    markdown_str += render_dict_as_bullets(item, level+1)
                else:
                    markdown_str += f"{'    '*(level+1)}- {item}\n"
        else:
            if isinstance(v, bool):
                tick = "✓" if v else "✗"
                markdown_str += f"{indent}- **{title}**: {tick}\n"
            else:
                markdown_str += f"{indent}- **{title}**: {v}\n"
    return markdown_str


def initialize_session_state():
    """Initialize session state variables needed for transcript views."""
    if "refresh_counter" not in st.session_state:
        st.session_state.refresh_counter = 0


def delete_and_refresh(interview_id, type):
    """Delete an interview and refresh the display."""
    with st.spinner("Deleting interview..."):
        if delete_interview(interview_id, type):
            st.success("Interview deleted successfully.")
        else:
            st.error("Failed to delete interview.")
        st.session_state.refresh_counter += 1


def reanalyse_and_refresh(interview_id, type):
    """Reanalyze a transcript and refresh the display."""
    with st.spinner("Analysing transcript..."):
        if reanalyse_transcript(interview_id, type):
            st.success("Transcript analysed successfully.")
        else:
            st.error("Failed to analyse transcript.")
        st.session_state.refresh_counter += 1


def safe_render_field(interview, key, label, render_type="text"):
    """Safely render a field from an interview document."""
    try:
        val = interview.get(key)
        if val is not None:
            if render_type == "text":
                st.write(f"{label}: {val}")
            elif render_type == "json":
                st.json(val)
    except Exception as e:
        st.error(f"Error rendering {label}: {e}")


def render_time_data(time_data):
    """Render time-related data from an interview."""
    if time_data and isinstance(time_data, dict):
        try:
            st_ts = time_data.get("start_time")
            curr_ts = time_data.get("current_time")
            if st_ts:
                st_date = datetime.fromtimestamp(st_ts)
                date_str = st_date.strftime("%d %b %Y")
                st.write(f"Date: {date_str}")
            if st_ts and curr_ts:
                duration_val = time_data.get("duration_so_far")
                if duration_val is None:
                    duration_val = curr_ts - st_ts
                duration_formatted = str(
                    timedelta(seconds=duration_val)).split(".")[0]
                st.write(f"Duration: {duration_formatted}")
        except Exception as e:
            st.error(f"Error parsing time data: {e}")


def render_analysis_date(analyzed_at, title="Analysis"):
    """Render the analysis date with proper formatting."""
    if analyzed_at:
        try:
            if isinstance(analyzed_at, str):
                analyzed_at = datetime.fromisoformat(analyzed_at)
            formatted_date = analyzed_at.strftime("%d %b %Y %H:%M")
            return f"### {title} (analysed on {formatted_date})"
        except Exception as e:
            print(f"Error formatting analyzed_at date: {e}")
    return f"### {title}"


def render_student_interviews(container):
    """Render student interviews with their analyses."""
    with container:
        try:
            with st.spinner("Loading interviews..."):
                interviews = get_interviews(type="Student")
            if interviews:
                for interview in interviews:
                    username = interview.get("username", "Unknown")
                    with st.expander(
                        f"## Interview with {username}",
                        expanded=True
                    ):
                        # Interview details section
                        with st.container():
                            st.markdown("### Interview Details")
                            safe_render_field(
                                interview, "college", "College", "text")
                            safe_render_field(
                                interview, "age_group", "Age Group", "text")
                            safe_render_field(
                                interview, "gender", "Gender", "text")
                            render_time_data(interview.get("time_data"))
                            completed = interview.get("completed")
                            if completed is not None:
                                tick = "✓" if completed else "✗"
                                st.write(f"Completed: {tick}")

                        # Responses section
                        with st.container():
                            responses = interview.get("responses")
                            isAnalysed = responses and isinstance(
                                responses, dict)
                            if isAnalysed:
                                title = render_analysis_date(
                                    interview.get("analyzed_at"),
                                    "Student Analysis"
                                )
                                st.markdown(title)
                                st.markdown(render_dict_as_bullets(responses))

                        # Sentiment analysis section
                        with st.container():
                            sentiments = interview.get("sentiment_analysis")
                            if sentiments and isinstance(sentiments, dict):
                                title = render_analysis_date(interview.get(
                                    "analyzed_at"), "Sentiment Analysis")
                                st.markdown(title)
                                st.markdown(render_dict_as_bullets(sentiments))

                        # Transcript section
                        with st.container():
                            st.markdown("### Transcript")
                            transcript = interview.get("transcript")
                            if transcript and isinstance(transcript, str):
                                st.text_area(
                                    "",
                                    transcript,
                                    height=200,
                                    key={interview.get("_id")}
                                )

                        # Actions section
                        st.write(" ")
                        st.write(" ")
                        cols = st.columns([1, 1])
                        with cols[0]:
                            st.download_button(
                                label="Download Transcript",
                                data=interview.get("transcript", ""),
                                file_name=(
                                    f"{interview.get('username', 'unknown')}"
                                    "_transcript.txt"
                                ),
                                mime="text/plain"
                            )
                        with cols[1]:
                            col1, col2 = st.columns([1, 1])
                            if not isAnalysed:
                                with col1:
                                    st.button(
                                        "Analyse",
                                        key=f"analyse-{interview.get('_id')}",
                                        on_click=reanalyse_and_refresh,
                                        args=(
                                            interview.get('_id'),
                                            "Student"
                                        ),
                                        use_container_width=True
                                    )
                            with col2:
                                st.button(
                                    "Delete",
                                    key=f"delete-{interview.get('_id')}",
                                    on_click=delete_and_refresh,
                                    args=(
                                        interview.get('_id'),
                                        "Student"
                                    ),
                                    use_container_width=True
                                )
            else:
                st.info(
                    "No student interview responses found in the database."
                )
        except Exception as e:
            st.error(f"Error fetching student interview responses: {e}")


def render_staff_interviews(container):
    """Render staff interviews with their analyses."""
    with container:
        try:
            with st.spinner("Loading interviews..."):
                interviews = get_interviews(type="Staff")
            if interviews:
                for interview in interviews:
                    username = interview.get("username", "Unknown")
                    with st.expander(
                        f"## Interview with {username}",
                        expanded=True
                    ):
                        # Interview details section
                        with st.container():
                            st.markdown("### Interview Details")
                            safe_render_field(
                                interview, "college", "College", "text")
                            safe_render_field(
                                interview, "age_group", "Age Group", "text")
                            safe_render_field(
                                interview, "gender", "Gender", "text")
                            render_time_data(interview.get("time_data"))
                            completed = interview.get("completed")
                            if completed is not None:
                                tick = "✓" if completed else "✗"
                                st.write(f"Completed: {tick}")

                        # Responses section
                        with st.container():
                            responses = interview.get("responses")
                            isAnalysed = responses and isinstance(
                                responses, dict)
                            if responses and isinstance(responses, dict):
                                title = render_analysis_date(
                                    interview.get("analyzed_at"),
                                    "Staff Analysis"
                                )
                                st.markdown(title)
                                st.markdown(render_dict_as_bullets(responses))

                        # Transcript section
                        with st.container():
                            st.markdown("### Transcript")
                            transcript = interview.get("transcript")
                            if transcript and isinstance(transcript, str):
                                st.text_area(
                                    "",
                                    transcript,
                                    height=200,
                                    key={interview.get("_id")}
                                )

                        # Actions section
                        st.write(" ")
                        st.write(" ")
                        cols = st.columns([1, 1])
                        with cols[0]:
                            st.download_button(
                                label="Download Transcript",
                                data=interview.get("transcript", ""),
                                file_name=(
                                    f"{interview.get('username', 'unknown')}"
                                    "_transcript.txt"
                                ),
                                mime="text/plain"
                            )
                        with cols[1]:
                            col1, col2 = st.columns([1, 1])
                            if not isAnalysed:
                                with col1:
                                    st.button(
                                        "Analyse",
                                        key=f"analyse-{interview.get('_id')}",
                                        on_click=reanalyse_and_refresh,
                                        args=(
                                            interview.get('_id'),
                                            "Staff"
                                        ),
                                        use_container_width=True)
                            with col2:
                                st.button(
                                    "Delete",
                                    key=f"delete-{interview.get('_id')}",
                                    on_click=delete_and_refresh,
                                    args=(
                                        interview.get('_id'),
                                        "Staff"
                                    ),
                                    use_container_width=True
                                )
            else:
                st.info("No staff interview responses found in the database.")
        except Exception as e:
            st.error(f"Error fetching staff interview responses: {e}")
