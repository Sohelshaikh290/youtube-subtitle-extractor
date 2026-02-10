import streamlit as st
import yt_dlp
import os
import tempfile
import re
from typing import Tuple, Optional
from datetime import timedelta

# --- Page Configuration ---
st.set_page_config(
    page_title="YouTube Subtitle Pro",
    page_icon="📜",
    layout="wide"
)

# --- Custom Styles ---
st.markdown("""
    <style>
    .main { max-width: 1000px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF0000; color: white; }
    .stButton>button:hover { background-color: #CC0000; color: white; border: none; }
    .video-info-container { display: flex; gap: 20px; margin-bottom: 20px; align-items: flex-start; }
    </style>
    """, unsafe_allow_html=True)

def strip_vtt_timestamps(vtt_text: str) -> str:
    """Simple regex to remove VTT/SRT timestamps and metadata for a clean transcript."""
    # Remove header
    text = re.sub(r'WEBVTT/n.*?\n\n', '', vtt_text, flags=re.DOTALL)
    # Remove timestamps (00:00:00.000 --> 00:00:00.000)
    text = re.sub(r'\d{1,2}:\d{2}:\d{2}\.\d{3} --> \d{1,2}:\d{2}:\d{2}\.\d{3}.*?\n', '', text)
    # Remove SRT style timestamps (00:00:00,000)
    text = re.sub(r'\d{1,2}:\d{2}:\d{2},\d{3} --> \d{1,2}:\d{2}:\d{2},\d{3}.*?\n', '', text)
    # Remove tags like <c> or <i>
    text = re.sub(r'<[^>]*>', '', text)
    # Remove line numbers
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    # Collapse multiple newlines
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def get_info(url: str, cookies_path: Optional[str] = None):
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'cookiefile': cookies_path if cookies_path else None
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        st.error(f"Extraction Error: {str(e)}")
        return None

def process_subtitles(url: str, sub_code: str, is_auto: bool, cookies_path: str, clean_text: bool) -> Tuple[Optional[bytes], str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        # We use a generic template to find the file easily, then rename it later
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': not is_auto,
            'writeautomaticsub': is_auto,
            'subtitleslangs': [sub_code],
            'outtmpl': os.path.join(tmpdir, 'downloaded_sub'),
            'cookiefile': cookies_path if cookies_path else None,
            'postprocessors': [{'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'}] if not clean_text else [],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # EXACT video title including emojis and symbols
                video_title = info.get('title', 'subtitles')
                
                files = os.listdir(tmpdir)
                if not files:
                    return None, ""
                
                source_file = os.path.join(tmpdir, files[0])
                ext = os.path.splitext(files[0])[1]
                
                with open(source_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if clean_text:
                    content = strip_vtt_timestamps(content)
                    final_name = f"{video_title}.txt"
                    return content.encode('utf-8'), final_name
                else:
                    final_name = f"{video_title}{ext}"
                    return content.encode('utf-8'), final_name
                    
        except Exception as e:
            st.error(f"Processing failed: {e}")
            return None, ""

# --- UI Layout ---
st.title("📜 YouTube Subtitle Pro")
st.caption("Extract exact transcripts or subtitle files including emojis and symbols in the filename.")

col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("Settings")
    use_cookies = st.toggle("Enable Cookies", help="Required for private/age-gated videos")
    cookie_file = None
    if use_cookies:
        cookie_file = st.file_uploader("Upload cookies.txt", type=['txt'])
    
    clean_mode = st.toggle("Clean Transcript Mode", value=True, help="Removes timestamps for easy reading.")

with col1:
    url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
    
    if url:
        cookies_path = None
        if use_cookies and cookie_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
                tmp.write(cookie_file.getvalue())
                cookies_path = tmp.name

        with st.status("Analyzing video metadata...") as status:
            info = get_info(url, cookies_path)
            if info:
                status.update(label="Analysis Complete!", state="complete")
        
        if info:
            # Video Details Section
            title = info.get('title', 'Unknown Title')
            thumbnail = info.get('thumbnail')
            duration_seconds = info.get('duration')
            duration_str = str(timedelta(seconds=duration_seconds)) if duration_seconds else "Unknown"

            st.write(f"### {title}")
            
            v_col1, v_col2 = st.columns([1, 2])
            with v_col1:
                if thumbnail:
                    st.image(thumbnail, use_container_width=True)
            with v_col2:
                st.write(f"**Duration:** {duration_str}")
                st.write(f"**Channel:** {info.get('uploader', 'Unknown')}")
                st.write(f"**Views:** {info.get('view_count', 0):,}")

            st.divider()
            
            manual = info.get('subtitles', {})
            auto = info.get('automatic_captions', {})
            
            options = []
            for k, v in manual.items():
                options.append({"label": f"✅ {v[0].get('name', k)} (Manual)", "code": k, "auto": False})
            for k, v in auto.items():
                options.append({"label": f"🤖 {v[0].get('name', k)} (Auto)", "code": k, "auto": True})
            
            if not options:
                st.warning("No subtitles detected for this video.")
            else:
                selection = st.selectbox(
                    "Choose Language & Type", 
                    options, 
                    format_func=lambda x: x['label']
                )
                
                if st.button("Generate Download"):
                    data, name = process_subtitles(
                        url, 
                        selection['code'], 
                        selection['auto'], 
                        cookies_path, 
                        clean_mode
                    )
                    
                    if data:
                        st.balloons()
                        st.download_button(
                            label=f"💾 Download {name}",
                            data=data,
                            file_name=name,
                            mime="text/plain" if clean_mode else "text/vtt"
                        )

        # Cleanup
        if cookies_path and os.path.exists(cookies_path):
            os.remove(cookies_path)

st.divider()
st.markdown("Developed with ❤️ using Streamlit & yt-dlp")
