import streamlit as st

def main():
    st.set_page_config(
        page_title="Privacy Notice - AI Research in FE Colleges",
        page_icon="🔒",
        layout="centered"
    )
    
    st.title("Privacy Notice for Research on AI Use in FE Colleges")
    
    st.markdown("""
    ## 1. Introduction
    
    This privacy notice explains how the Gatsby Foundation collects, uses, and protects
    personal data during its research on AI use in Further Education colleges. The research
    examines how students interact with AI in their studies and daily lives and explores their
    perceptions of its impact on future careers.
    
    Data collected in this research is processed and stored by Founders & Coders on behalf of
    Gatsby, which retains overall control of the data as the data controller.
    """)
    
    st.markdown("""
    ## 2. What Data We Collect
    
    To understand trends in AI use, we will collect the following personal data from student
    participants:
    
    * **Age range**: Under 25 or Over 25 – This helps compare attitudes to AI between
    younger and older students.
    * **Gender**: Studies show gender differences in attitudes towards technology and
    careers in IT. We aim to assess whether these trends apply to AI.
    * **College Name**: To identify patterns across different institutions and educational
    settings.
    * **Subjects Being Studied**: To explore whether AI usage and attitudes vary by subject
    area.
    * **AI Interaction Responses**: We will collect the text-based responses generated
    through an AI chat interface, which allows students to interact with a large language
    model (LLM) and receive generated questions.
    
    No directly identifiable personal data such as names or contact details will be requested.
    However, respondents should be aware that free-text responses could contain identifying
    information.
    """)
    
    st.markdown("""
    ## 3. How We Use Your Data
    
    Your data will be used to:
    
    * Analyse trends in AI usage and attitudes among FE students.
    * Identify patterns based on age, gender, college, and subject choices.
    * Generate insights to support educational policy and practice.
    
    The chatbot is deployed on Streamlit, but no data is permanently stored there. Collected
    data is securely stored in a MongoDB database, which is managed with appropriate security
    measures to protect your information. If there is a database server issue, transcripts and
    analysis can be temporarily stored on Streamlit until the connection is resumed and the
    data is sent to the secure database, after which the data on Streamlit is removed.
    """)
    
    st.markdown("""
    ## 4. AI and Third-Party Data Processing
    
    Our AI chat interface is powered by third-party providers such as OpenAI or Anthropic.
    During processing, both pre- and post-anonymisation data may be temporarily handled by
    these providers. For example, OpenAI retains interaction data for 30 days for abuse
    monitoring and does not use it for training unless explicitly opted in. We document this
    processing and have reviewed their data retention policies to ensure compliance.
    """)
    
    st.markdown("""
    ## 5. Data Retention and Anonymisation
    
    * **Data anonymisation**: During the processing phase, any information that could
    identify individuals beyond the required demographic categories will be removed.
    * **Data retention**: OpenAI retains interaction data (before and after anonymisation) for
    30 days for abuse monitoring but does not use it for model training unless explicitly
    opted in. No personal data will be knowingly stored for the purpose of this research.
    * Complete anonymisation may not be fully achievable due to our limited control over
    external AI processing.
    """)
    
    st.markdown("""
    ## 6. Risk Management and Compliance
    
    A Record of Processing Activities (ROPA) will be maintained dynamically as responses are
    collected to track and mitigate any risks of identifiable data being inadvertently disclosed.
    Participants should be aware that free-text responses could potentially contain self-
    identifying details, which will be removed where feasible.
    """)
    
    st.markdown("""
    ## 7. Legal Basis for Processing
    
    Our legal basis under UK GDPR is primarily legitimate interest, supported by a completed
    Data Protection Impact Assessment (DPIA) to assess risks and ensure appropriate
    safeguards. We also adhere to data sharing best practices, including potential agreements
    with participating colleges and third-party processors.
    """)
    
    st.markdown("""
    ## 8. Your Rights
    
    Under data protection laws, you have the right to:
    
    * Download a copy of your transcript and associated analysis when it is being
    processed.
    * Request correction or deletion, only during the same session when it is being
    processed
    * Object to processing under certain circumstances
    
    Unfortunately we are not able to handle requests for data and deletion after the
    session is complete and the anonymised data processed and stored. After this stage,
    it is no longer identifiable as being connected to a specific individual and therefore
    such requests are not possible as it ceases to be personal data.
    """)
    
    st.markdown("""
    ## 9. Further Information
    
    For more details on data protection at Gatsby, please see the Gatsby Foundation Privacy
    Notice.
    
    If you have any questions about this research project and its data use, please contact Daniel
    Sandford Smith at ds@gatsby.org.uk
    """)
    
    st.divider()
    
    st.markdown("""
    By continuing with this research activity, you acknowledge that you have read and understood
    this privacy notice.
    """)
    
    # Optional: Add acknowledgment button
    if st.button("I Acknowledge the Privacy Notice"):
        st.success("Thank you for acknowledging the privacy notice. You may now proceed with the research activity.")

if __name__ == "__main__":
    main()