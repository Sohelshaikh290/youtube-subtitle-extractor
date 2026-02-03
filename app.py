import streamlit as st
import yt_dlp
import os
import tempfile
import time

# Page Configuration
st.set_page_config(
    page_title="YouTube Subtitle Extractor",
    page_icon="🎬",
    layout="centered"
)

# App Title and Description
st.title("🎬 YouTube Subtitle Extractor")
st.markdown("""
Extract manual or auto-generated subtitles from any YouTube video. 
Paste your link below to get started.
""")

# Sidebar for Cookies (Advanced)
with st.sidebar:
    st.header("Settings")
    use_cookies = st.checkbox("Use Cookies (.txt)", help="Required for age-restricted or private videos.")
    cookie_file = None
    if use_cookies:
        cookie_file = st.file_uploader("Upload cookies.txt", type=["txt"])

def get_video_info(url, cookies_path=None):
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    if cookies_path:
        ydl_opts['cookiefile'] = cookies_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None

def download_subtitle(url, sub_code, is_auto, cookies_path=None):
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Define base options
        # We use a generic template first, then rename to remove language suffixes
        ydl_opts = {
            'skip_download': True,
            'outtmpl': os.path.join(tmpdirname, '%(title)s.%(ext)s'),
            'subtitleslangs': [sub_code],
            'writesubtitles': not is_auto,
            'writeautomaticsub': is_auto,
            'quiet': True,
            'noplaylist': True,
        }
        
        if cookies_path:
            ydl_opts['cookiefile'] = cookies_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info again to get the clean title for the final filename
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'subtitles')
                ydl.download([url])
            
            # Find the downloaded subtitle file (it usually has a .en.vtt or similar suffix)
            files = os.listdir(tmpdirname)
            if files:
                original_file_path = os.path.join(tmpdirname, files[0])
                file_extension = os.path.splitext(files[0])[1] # e.g., .vtt or .srt
                
                # Create the clean filename: Video Title.extension
                clean_filename = f"{video_title}{file_extension}"
                # Remove characters that might be illegal in filenames just in case
                clean_filename = "".join([c for c in clean_filename if c.isalnum() or c in (' ', '.', '-', '_')]).strip()
                
                final_file_path = os.path.join(tmpdirname, clean_filename)
                os.rename(original_file_path, final_file_path)
                
                with open(final_file_path, "rb") as f:
                    return f.read(), clean_filename
            return None, None
        except Exception as e:
            st.error(f"Download Error: {str(e)}")
            return None, None

# Main UI Logic
video_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

if video_url:
    # Handle Cookies
    cookies_path = None
    if use_cookies and cookie_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_cookie:
            tmp_cookie.write(cookie_file.getvalue())
            cookies_path = tmp_cookie.name

    with st.spinner("Analyzing video..."):
        info = get_video_info(video_url, cookies_path)

    if info:
        st.subheader(info.get('title', 'Video Found'))
        if 'thumbnail' in info:
            st.image(info['thumbnail'], width=300)

        # Process Subtitles
        manual_subs = info.get('subtitles', {})
        auto_subs = info.get('automatic_captions', {})
        
        available_options = []
        
        for lang_code, details in manual_subs.items():
            name = details[0].get('name', lang_code)
            available_options.append({
                "label": f"{name} (Manual)",
                "code": lang_code,
                "is_auto": False
            })
            
        for lang_code, details in auto_subs.items():
            name = details[0].get('name', lang_code)
            available_options.append({
                "label": f"{name} (Auto-generated)",
                "code": lang_code,
                "is_auto": True
            })

        if not available_options:
            st.warning("No subtitles found for this video.")
        else:
            # Selection UI
            selection_labels = [opt['label'] for opt in available_options]
            choice_label = st.selectbox("Select Subtitle Track", selection_labels)
            
            # Find selected option data
            selected_opt = next(opt for opt in available_options if opt['label'] == choice_label)
            
            if st.button("Prepare Download"):
                with st.spinner("Processing file..."):
                    file_data, file_name = download_subtitle(
                        video_url, 
                        selected_opt['code'], 
                        selected_opt['is_auto'], 
                        cookies_path
                    )
                    
                    if file_data:
                        st.success(f"Ready: {file_name}")
                        st.download_button(
                            label="Click to Download File",
                            data=file_data,
                            file_name=file_name,
                            mime="text/plain" # Generic text mime to handle various sub formats
                        )
                    else:
                        st.error("Failed to generate download. Try a different format.")

    # Cleanup temp cookie file if created
    if cookies_path and os.path.exists(cookies_path):
        os.remove(cookies_path)

st.divider()
st.caption("Built with Streamlit and yt-dlp")
