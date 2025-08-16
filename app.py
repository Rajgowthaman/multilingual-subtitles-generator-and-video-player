import streamlit as st
import tempfile
import base64
import os
import subprocess
from faster_whisper import WhisperModel
from googletrans import Translator

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Video Translator with Inline Subtitles", layout="wide")
st.title("🎬 Video Translator + Inline Subtitle Player")

# Whisper Model (change to "medium" or "large-v3" for better accuracy)
model_size = "small"
whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
translator = Translator()

# ----------------------------
# FUNCTIONS
# ----------------------------
def extract_audio(video_path, audio_path):
    """Extract audio from video using ffmpeg"""
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "mp3", audio_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def transcribe_audio(audio_path, source_lang):
    """Transcribe using Whisper"""
    segments, _ = whisper_model.transcribe(audio_path, language=source_lang)
    return list(segments)

def translate_segments(segments, target_lang):
    """Translate text segments"""
    translated_segments = []
    for seg in segments:
        text = translator.translate(seg.text, dest=target_lang).text
        translated_segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": text
        })
    return translated_segments

def create_vtt(segments, file_path):
    """Create a WebVTT subtitle file"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for seg in segments:
            start_time = format_timestamp(seg["start"])
            end_time = format_timestamp(seg["end"])
            f.write(f"{start_time} --> {end_time}\n{seg['text']}\n\n")

def format_timestamp(seconds):
    """Convert seconds to WebVTT timestamp format"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds * 1000) % 1000)
    return f"{hrs:02}:{mins:02}:{secs:02}.{ms:03}"

def get_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ----------------------------
# UI
# ----------------------------
uploaded_video = st.file_uploader("Upload a Video", type=["mp4", "mov", "mkv"])
source_lang = st.selectbox("Source Language", ["en", "ta", "fr", "es", "de", "zh", "hi"])
target_lang = st.selectbox("Target Language", ["en", "ta", "fr", "es", "de", "zh", "hi"])

if uploaded_video and st.button("Generate Subtitled Player"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        temp_video.write(uploaded_video.read())
        video_path = temp_video.name

    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    temp_subs = tempfile.NamedTemporaryFile(delete=False, suffix=".vtt").name

    # Progress 1: Audio Extraction
    with st.spinner("Extracting audio..."):
        extract_audio(video_path, temp_audio)

    # Progress 2: Transcription
    with st.spinner("Transcribing audio..."):
        segments = transcribe_audio(temp_audio, source_lang)

    # Progress 3: Translation
    with st.spinner("Translating subtitles..."):
        translated_segments = translate_segments(segments, target_lang)

    # Progress 4: Subtitle File Creation
    create_vtt(translated_segments, temp_subs)

    # Convert to base64 for embedding
    video_b64 = get_base64(video_path)
    subs_b64 = get_base64(temp_subs)

    video_data_uri = f"data:video/mp4;base64,{video_b64}"
    subs_data_uri = f"data:text/vtt;base64,{subs_b64}"

    # Show mini player at the bottom
    st.markdown("---")
    st.subheader("Preview with Subtitles")
    video_html = f"""
    <video controls width="640" style="border-radius:10px;" crossorigin="anonymous">
        <source src="{video_data_uri}" type="video/mp4">
        <track src="{subs_data_uri}" kind="subtitles" srclang="{target_lang}" label="{target_lang.upper()}" default>
        Your browser does not support the video tag.
    </video>
    """
    st.markdown(video_html, unsafe_allow_html=True)

    st.success("✅ Done! Subtitles are shown in the player.")

    # Cleanup
    os.remove(video_path)
    os.remove(temp_audio)
    os.remove(temp_subs)