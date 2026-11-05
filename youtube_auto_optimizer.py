import os
import google.generativeai as genai
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# 1. GitHub Secrets se credentials load karna
API_KEY = os.environ.get("YOUTUBE_API_KEY")
CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CLIENT_ID = os.environ.get("YT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YT_REFRESH_TOKEN")

# 2. Gemini API Configure karna
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def get_authenticated_service():
    """OAuth 2.0 ke zariye YouTube authenticated service banata hai"""
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"]
    )
    return build("youtube", "v3", credentials=creds)

def get_channel_videos(youtube, max_results=35):
    """Channel se videos ki list (ID, Title, Description, Tags) nikalta hai"""
    # Pehle channel ki 'Uploads' playlist ID nikalte hain
    ch_request = youtube.channels().list(part="contentDetails", id=CHANNEL_ID)
    ch_response = ch_request.execute()
    uploads_playlist_id = ch_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    videos = []
    next_page_token = None

    while len(videos) < max_results:
        pl_request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=min(50, max_results - len(videos)),
            pageToken=next_page_token
        )
        pl_response = pl_request.execute()

        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in pl_response["items"]]
        
        # Videos ki poori details (statistics, snippet) lene ke liye
        v_request = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids)
        )
        v_response = v_request.execute()

        for v in v_response["items"]:
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "description": v["snippet"]["description"],
                "tags": v["snippet"].get("tags", [])
            })

        next_page_token = pl_response.get("nextPageToken")
        if not next_page_token or len(videos) >= max_results:
            break

    return videos[:max_results]

def optimize_with_gemini(title, description):
    """Gemini 2.5-flash se behtareen SEO Title, Description aur Tags generate karwata hai"""
    prompt = f"""
    Aap ek expert YouTube SEO Optimizer hain. Niche diye gaye YouTube video ke title aur description ko analyze karein aur ek behtareen, engaging, aur search-friendly SEO package generate karein.
    
    Current Title: {title}
    Current Description: {description}

    Kripya output strictly is format me dein (kisi aur extra text ke bina):
    TITLE: [Naya optimized aur catchy title yahan likhein]
    DESCRIPTION: [Optimized description with proper keywords and tags summary yahan likhein]
    TAGS: [comma separated tags yahan likhein, jaise: tag1, tag2, tag3]
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Parsing response safely
        lines = text.split("\n")
        opt_title = title
        opt_desc = description
        opt_tags = []

        for line in lines:
            if line.startswith("TITLE:"):
                opt_title = line.replace("TITLE:", "").strip()
            elif line.startswith("DESCRIPTION:"):
                opt_desc = line.replace("DESCRIPTION:", "").strip()
            elif line.startswith("TAGS:"):
                tags_str = line.replace("TAGS:", "").strip()
                opt_tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        return opt_title, opt_desc, opt_tags
    except Exception as e:
        print(f"Gemini Error: {e}")
        return title, description, []

def update_video_metadata(youtube, video_id, new_title, new_description, new_tags):
    """YouTube API ke zariye video ke metadata ko update karta hai"""
    try:
        # Pehle current snippet fetch karte hain taaki category ya baaki cheezein disturb na ho
        v_request = youtube.videos().list(part="snippet", id=video_id)
        v_response = v_request.execute()
        
        if not v_response["items"]:
            return
        
        snippet = v_response["items"][0]["snippet"]
        snippet["title"] = new_title
        snippet["description"] = new_description
        if new_tags:
            snippet["tags"] = new_tags

        update_request = youtube.videos().update(
            part="snippet",
            body={
                "id": video_id,
                "snippet": snippet
            }
        )
        update_request.execute()
        print(f"Successfully Optimized & Updated: {new_title}")
    except Exception as e:
        print(f"Update Error for video {video_id}: {e}")

def main():
    print("YouTube Auto SEO Optimizer Started...")
    youtube = get_authenticated_service()
    
    # 35 videos ka audit (Aap chahein toh ise badal bhi sakte hain)
    videos = get_channel_videos(youtube, max_results=35)
    print(f"Total {len(videos)} videos fetched for optimization check.")

    for v in videos:
        print(f"\nProcessing: {v['title']}")
        new_title, new_desc, new_tags = optimize_with_gemini(v['title'], v['description'])
        
        # Video update execute karein
        update_video_metadata(youtube, v['id'], new_title, new_desc, new_tags)

    print("\nAll tasks completed successfully!")

if __name__ == "__main__":
    main()
      
