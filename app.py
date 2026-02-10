import streamlit as st
import yt_dlp
import os
import tempfile
import re
from typing import Tuple, Optional
from datetime import timedelta

# --- Constants ---
LOGO_URL = "https://lh3.googleusercontent.com/rd-gg-dl/AOI_d_9o2hw_Yx_XXW7NW_dI6A2PtJToF5bb4iaczVrif3n-n53LNOsk7XCqlsjb9ufv4SYRGf4LBavqvepDwq7vGMNASxCuSFc5gRZQHl0RQVHGATVPS8axjhMDgchKQ-mTnobwf-AKvZlFVxbovmKxSW8n8_1Eh3i32hsMvSRzcRwY39gyOwB1CqkiEaR8vmv7TPXuTbRVV--VMQ2t2XUr-XpqimzCsOYIs7iMgU0ix_eun2PTB5Nqm7ApfvS3nPJeax3uWHLBE_-JWmoXU2swdxQXrxiA-kdljoAKpKusvATsk3asxk1XO9B8aasLn2qPAXT7Ifu5MjMUulbtM8eYPywWq4I0Rz1SZ5MOv_7SLh0ua_taSJBK4MUFD3CyBdchFUdWjrgMoEkUQIFYV-3HERdfoWSz7VmvRsth1_apdaOn1nTAz58N7QXEUBdW_Svo2rxxG3AuKClZbhNoRl5vngoL7v-OT-dcV3O-fAzsHw3EINL4LyqgSwl2Fzb39Z9yZjFH6MsbzHvrnsdk5ocA6X4eLDjgXF-4xA-GBQTbnFjYatADWrBxDh8vlMlZwJvZvDqI-x0drqc0N8AhFA4B-vw2UnvDHUDtIitmeNDdhv6J7xiJObDxrfMHT37hvrjF7ZjvI6KOjX8H_RtE6BuVpoNgS-qCTWiOBZf8CJNvHPvAORMMR9OrvYbUaM6JcMleBu0F0vDzzqlP6HtgYd-qtgg0oPajh_UZfaePGZnDDyJdEskoCHy1AoOMWYylCvzMHB9dChUmKs9N8m3hDWjYbQyXfGL8r_N6UGDgRSHQyk3w0jL-xM_85A4sXI2r_i0zc-AXRL242BD9xsPoXDwKsoKUVfrofZJoIvh7C5ODYtjQ6XSu6C2ybqffOzjNskWNPdEGoqUI9MOWVXR2FjTAm-h1wh1YdUgQTkC2IqpZrbwtYXQqns0CBOyEuP_IqAtCDlEf-Eq5-iw7mNDcuMa5kmeYsMAs907bBnCJin4DaJI3Zde7n2TK2ehxgtB33npLHD_JAn9OvxDIysAYCaMzERv9-jgW-oY45wphowZKA70INg83zMGxvrp_5HLXyxmiUiUYwqGwiz9OeM_xTCMRs3Ek3I_hF_a0MoN3kh0LxvBm9TgzrtZefUq75MW9mgvyBK0T_Z9dnA-ujn9kBdqloQaYSOMFrJxO92dnPPM_CDBeugc4k9niUBlrTasx5O4zCYfRXO0QrAwMauGMTzRR8ONP5XONTl0W8efCW1FqAntuRwc3xw0X-cNmZv2dWVCz=s1024-rj"

# --- Page Configuration ---
st.set_page_config(
    page_title="YouTube Subtitle Pro",
    page_icon=LOGO_URL,
    layout="wide"
)

# --- Custom Styles ---
st.markdown(f"""
    <style>
    .main {{ max-width: 1000px; margin: 0 auto; }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: #FF0000; color: white; border: none; font-weight: bold; }}
    .stButton>button:hover {{ background-color: #CC0000; color: white; border: none; }}
    .video-info-container {{ display: flex; gap: 20px; margin-bottom: 20px; align-items: flex-start; }}
    .header-container {{ display: flex; align-items: center; gap: 15px; margin-bottom: 10px; }}
    .header-logo {{ width: 50px; border-radius: 8px; }}
    </style>
    """, unsafe_allow_html=True)

def strip_vtt_timestamps(vtt_text: str) -> str:
    """Simple regex to remove VTT/SRT timestamps and metadata for a clean transcript."""
    # Remove header
    text = re.sub(r'WEBVTT\n.*?\n\n', '', vtt_text, flags=re.DOTALL)
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
# Header with Logo
st.markdown(f"""
    <div class="header-container">
        <img src="{LOGO_URL}" class="header-logo">
        <h1 style="margin: 0;">YouTube Subtitle Pro</h1>
    </div>
    """, unsafe_allow_html=True)

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
