import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re
import base64

# Configure Gemini API Key
genai.configure(api_key="AIzaSyCFA8FGd9mF42_4ExVYTqOsvOeCbyHzBFU")

def extract_video_id(url):
    patterns = [
        r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]{11})",
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([\w-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        if 'en' in [t.language_code for t in transcript_list]:
            transcript = transcript_list.find_transcript(['en']).fetch()
        else:
            available_transcript = next(iter(transcript_list))
            transcript = available_transcript.translate('en').fetch()
        return " ".join([t["text"] for t in transcript])
    except (TranscriptsDisabled, NoTranscriptFound):
        return "No transcript available."
    except Exception as e:
        return f"Error: {str(e)}"

def summarize_text(text, level="medium"):
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"Summarize in {level} detail:\n\n{text}"
    response = model.generate_content(prompt)
    return response.text

def generate_mcqs(text, num_questions=5, difficulty="medium"):
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"Generate {num_questions} MCQs with {difficulty} difficulty from:\n{text}. Format as: Question | Option1 | Option2 | Option3 | Option4 | CorrectOptionNumber"
    response = model.generate_content(prompt)
    
    mcq_list = []
    for line in response.text.split("\n"):
        parts = line.split("|")
        if len(parts) == 6:
            try:
                mcq_list.append({
                    "question": parts[0].strip(),
                    "options": [parts[1].strip(), parts[2].strip(), parts[3].strip(), parts[4].strip()],
                    "answer": int(parts[5].strip()) - 1  # Convert to 0-based index
                })
            except ValueError:
                pass  # Skip if answer is not a valid integer
    return mcq_list

def create_download_link(data, filename, label):
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{label}</a>'
    return href

# -------------------- Streamlit UI --------------------
st.title("YouTube AI Tutor")  
st.write("Extract transcript, summarize, translate, generate MCQs, flashcards, and more!")

video_url = st.text_input("Enter YouTube Video URL:")
summary_level = st.radio("Summary detail:", ["short", "medium", "detailed"], index=1)
difficulty = st.radio("MCQ Difficulty:", ["easy", "medium", "hard"], index=1)
num_mcqs = st.slider("Number of MCQs:", 3, 10, 5)

download_links = ""

if st.button("Get Transcript"):
    video_id = extract_video_id(video_url)
    if video_id:
        with st.spinner("Fetching transcript..."):
            transcript = get_youtube_transcript(video_id)
            st.session_state["transcript"] = transcript
    else:
        st.warning("Invalid YouTube URL.")

if "transcript" in st.session_state:
    st.subheader("📜 Extracted Transcript")
    st.write(st.session_state["transcript"])
    download_links += create_download_link(st.session_state["transcript"], "transcript.txt", "Download Transcript") + " | "
    
    if st.button("Summarize Transcript"):
        with st.spinner("Generating summary..."):
            summary = summarize_text(st.session_state["transcript"], summary_level)
            st.session_state["summary"] = summary

if "summary" in st.session_state:
    st.subheader("📝 Summary")
    st.write(st.session_state["summary"])
    download_links += create_download_link(st.session_state["summary"], "summary.txt", "Download Summary") + " | "
    
    if st.button("Generate MCQs"):
        with st.spinner("Creating MCQs..."):
            mcqs = generate_mcqs(st.session_state["summary"], num_mcqs, difficulty)
            st.session_state["mcqs"] = mcqs

# -------------------- Interactive MCQ Test --------------------
if "mcqs" in st.session_state:
    st.subheader("✅ Multiple Choice Questions")

    score = 0
    user_answers = []

    for idx, mcq in enumerate(st.session_state["mcqs"]):
        st.write(f"**{idx+1}. {mcq['question']}**")
        selected_option = st.radio(f"Choose an answer:", mcq['options'], key=f"mcq_{idx}")
        
        # Fixing the error: Ensure answer is an integer before indexing
        correct_index = int(mcq["answer"])
        correct_answer = mcq["options"][correct_index] if 0 <= correct_index < len(mcq["options"]) else None

        if selected_option:
            user_answers.append((selected_option, correct_answer))

    if st.button("Submit Answers"):
        score = sum(1 for user_ans, correct_ans in user_answers if user_ans == correct_ans)
        st.success(f"🎉 You scored {score} out of {len(st.session_state['mcqs'])}!")

        download_links += create_download_link("\n".join([f"{q['question']} - Correct Answer: {q['options'][q['answer']]}" for q in st.session_state["mcqs"]]), "mcqs.txt", "Download MCQs")

if download_links:
    st.markdown(download_links, unsafe_allow_html=True)

st.write("🚀 AI-powered tutor that helps you learn faster!")  
