import streamlit as st
from summary_utils import generate_transcript_summary

# Sample transcript for testing
sample_transcript = """
interviewer: Hello! I appreciate your time today to discuss your experiences and thoughts on AI in learning. To start, could you tell me a bit about yourself? Feel free to share your age, gender (if comfortable), what you're studying, and what you hope to do next.
user: Hi! I'm 22, she/her, and I'm studying Computer Science at XYZ University. I'm hoping to get into software development after graduating, ideally working on AI applications.

interviewer: Thank you for sharing that. Could you tell me about your experiences using AI in your studies? Do you use AI tools for your coursework or research?
user: Yes, I use AI quite a lot for my studies. I mainly use ChatGPT to help explain complex programming concepts when I'm stuck. I also use GitHub Copilot when coding for projects. For research papers, I sometimes use AI to help summarize research papers and generate ideas.

interviewer: That's interesting. What aspects of these AI tools do you find most effective for your learning?
user: I find AI most helpful when I'm debugging code. It can quickly spot logic errors that I miss. Also, when I don't understand a concept from lectures, AI can explain it in different ways until it clicks. I like how it personalizes explanations based on my questions.

interviewer: And what about ineffective aspects? Are there times when AI tools don't meet your learning needs?
user: Sometimes the AI gives me incorrect code solutions that look right but don't work when implemented. For research, it can oversimplify complex topics or miss important nuances. It's also not great for creative problem-solving where you need novel approaches.

interviewer: How do your teachers or professors view the use of AI tools in your studies? Do they encourage or discourage their use?
user: It's mixed. Some professors are supportive and even recommend specific AI tools. Others are concerned about academic integrity and ban AI use on assignments. Most fall somewhere in the middle - they allow AI for learning but not for submitting work.

interviewer: Do you use AI outside of your studies, for personal or leisure activities?
user: Absolutely! I use AI to create digital art with Midjourney and DALL-E. I also have a smart home setup with Alexa for organization. I use AI writing tools for my blog too. It's generally more casual than my academic use - I'm less concerned about accuracy and more focused on creativity and fun.

interviewer: How do you think your learning institution could use AI to help students?
user: I think they could use AI for lesson planning to create more personalized learning paths. For feedback and marking, AI could provide initial comments that professors could then review, making the process faster while maintaining quality. For resource creation, AI could help generate study materials tailored to different learning styles.

interviewer: Do you have any concerns about AI in education?
user: Yes, I worry about over-reliance on AI. Students might lose critical thinking skills or the ability to work through difficult problems. In society, I'm concerned about bias in AI systems affecting important decisions. And in the workplace, I worry about job displacement, especially for entry-level positions that new graduates typically fill.

interviewer: How important do you think AI will be in your future career?
user: Extremely important. In software development, AI tools are already changing how we code. I feel somewhat prepared because I've been using these tools, but I need to develop more skills in prompt engineering and understanding machine learning fundamentals. I also want to learn more about data analysis to work effectively with AI systems.

interviewer: How do you think AI will change education, work, and daily life compared to what previous generations experienced?
user: In education, it's already creating more interactive and personalized learning experiences compared to the one-size-fits-all approach of the past. In work, automation will handle routine tasks, allowing people to focus on creative and strategic work. In daily life, AI assistants will continue to become more integrated, making everyday tasks more efficient in ways previous generations couldn't imagine.
"""

def main():
    # Set up page title
    st.set_page_config(page_title="Test Transcript Summary")
    st.title("Test Transcript Summary")
    
    # Button to trigger the summary generation
    if st.button("Generate Summary"):
        with st.spinner("Generating summary..."):
            try:
                # Call our function with the sample transcript
                st.write("Calling generate_transcript_summary...")
                summary = generate_transcript_summary(sample_transcript)
                
                # Display the result
                st.success("Summary generated successfully!")
                st.json(summary)
                
                # Show raw output
                st.subheader("Raw JSON")
                st.code(summary)
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.error("Check terminal for detailed traceback")

if __name__ == "__main__":
    main()