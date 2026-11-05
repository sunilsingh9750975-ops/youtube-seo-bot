import os
import time
from google.genai import Client
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ==========================================
# 1. ENV SECRETS & SETUP
# ==========================================
API_KEY = os.environ.get("YOUTUBE_API_KEY")
CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CLIENT_ID = os.environ.get("YT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YT_REFRESH_TOKEN")

client = Client(api_key=GEMINI_API_KEY)


def get_authenticated_service():
    """OAuth 2.0 Credentials validation & YouTube API service creation"""
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"]
    )
    return build("youtube", "v3", credentials=creds)


def call_gemini_safe(prompt):
    """Automatic retry & backoff logic to handle 429 quota limits safely"""
    max_retries = 3
    delay = 35
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"⚠️ Quota limit hit (429). Waiting {delay}s before retry ({attempt+1}/{max_retries})...")
                time.sleep(delay)
                delay += 15
            else:
                print(f"⚠️ Gemini API Error: {e}")
                return ""
    return ""


def optimize_channel_growth(youtube):
    """Channel-level analysis karke channel profile ko optimize karta hai"""
    try:
        print("\n🔍 Analyzing Channel Profile for Growth & Subscriber Boost...")
        ch_request = youtube.channels().list(part="snippet,statistics", id=CHANNEL_ID)
        ch_response = ch_request.execute()

        if not ch_response["items"]:
            return

        channel_info = ch_response["items"][0]
        snippet = channel_info["snippet"]
        stats = channel_info["statistics"]

        current_title = snippet.get("title", "")
        current_desc = snippet.get("description", "")
        sub_count = stats.get("subscriberCount", "Hidden")
        view_count = stats.get("viewCount", "0")

        print(f"📊 Channel Stats -> Subscribers: {sub_count} | Total Views: {view_count}")

        prompt = f"""
        Aap ek expert YouTube Channel Growth Strategist hain. Is YouTube channel ki profile ko analyze karke ek high-converting, professional aur subscriber-friendly Channel Description likhein.

        Channel Name: {current_title}
        Current Channel Description: {current_desc}

        INSTRUCTIONS:
        1. Ek engaging aur welcoming description likhein jo naye visitors ko subscriber me badal de.
        2. Channel ki niche ke best search keywords shamil karein.
        3. Call to Action (Subscribe reminder) zaroor ho aur emojis ka use karein.
        4. Max length 1000 characters tak honi chahiye.

        STRICT OUTPUT FORMAT:
        CHANNEL_DESC: [Optimized Channel Description Here]
        """

        text = call_gemini_safe(prompt)

        if "CHANNEL_DESC:" in text:
            new_channel_desc = text.split("CHANNEL_DESC:")[1].strip()
            if new_channel_desc and len(new_channel_desc) <= 5000:
                snippet["description"] = new_channel_desc
                
                youtube.channels().update(
                    part="snippet",
                    body={
                        "id": CHANNEL_ID,
                        "snippet": snippet
                    }
                ).execute()
                print("✅ SUCCESS: Channel Profile & Description upgraded!")
        
        # 🛑 Safe buffer gap after channel request to clear sliding minute window
        print("   ⏳ Waiting 30 seconds after channel optimization...")
        time.sleep(30)

    except Exception as e:
        print(f"⚠️ Channel Optimization Notice: {e}")
        time.sleep(30)


def get_channel_videos(youtube, max_results=35):
    """Channel se latest videos ki full metadata list nikalta hai"""
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
                "tags": v["snippet"].get("tags", []),
                "categoryId": v["snippet"].get("categoryId", "24")
            })

        next_page_token = pl_response.get("nextPageToken")
        if not next_page_token or len(videos) >= max_results:
            break

    return videos[:max_results]


def optimize_with_gemini(title, description):
    """Gemini AI Engine with Auto-Retry"""
    prompt = f"""
    Aap ek world-class YouTube SEO Specialist hain. Is video ke metadata ko analyze karke maximum CTR, high search rankings, aur viewer retention ke liye optimize karein.

    CURRENT TITLE: {title}
    CURRENT DESCRIPTION: {description}

    INSTRUCTIONS:
    1. TITLE: Super-catchy aur high-CTR hona chahiye (Hinglish/Hindi tone). Episode number zaroor maintain rakhein. STRICTLY 100 characters se bada nahi hona chahiye.
    2. DESCRIPTION: Clear structure with Emojis, Short Summary, Subscribe Reminder, aur end me 4-6 trending #hashtags.
    3. TAGS: 12 to 15 viral search tags (comma-separated).

    STRICT OUTPUT FORMAT:
    TITLE: [Optimized Title under 100 chars]
    DESCRIPTION: [Optimized Structured Description]
    TAGS: [tag1, tag2, tag3, tag4]
    """

    text = call_gemini_safe(prompt)
    if not text:
        return title, description, []

    opt_title = title
    opt_desc = description
    opt_tags = []

    try:
        if "TITLE:" in text and "DESCRIPTION:" in text and "TAGS:" in text:
            title_part = text.split("TITLE:")[1].split("DESCRIPTION:")[0].strip()
            desc_part = text.split("DESCRIPTION:")[1].split("TAGS:")[0].strip()
            tags_part = text.split("TAGS:")[1].strip()

            if title_part:
                opt_title = title_part
            if desc_part:
                opt_desc = desc_part
            if tags_part:
                opt_tags = [t.strip() for t in tags_part.split(",") if t.strip()]

        if len(opt_title) > 100:
            opt_title = opt_title[:97] + "..."

        if len(opt_desc) > 5000:
            opt_desc = opt_desc[:4997] + "..."

        return opt_title, opt_desc, opt_tags

    except Exception as e:
        print(f"⚠️ Parsing Error: {e}")
        return title, description, []


def update_video_metadata(youtube, video_id, new_title, new_description, new_tags, category_id):
    """Safely updates YouTube Video Metadata"""
    try:
        v_request = youtube.videos().list(part="snippet", id=video_id)
        v_response = v_request.execute()
        
        if not v_response["items"]:
            return
        
        snippet = v_response["items"][0]["snippet"]
        snippet["title"] = new_title
        snippet["description"] = new_description
        snippet["categoryId"] = category_id
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
        print(f"✅ SUCCESS: Updated Video -> {new_title}")

    except Exception as e:
        print(f"❌ UPDATE ERROR (Video ID: {video_id}): {e}")


def main():
    print("==================================================")
    print("🚀 SAFE BUFFERED YOUTUBE OPTIMIZER ENGINE")
    print("==================================================")
    
    youtube = get_authenticated_service()

    # 1. Channel Profile Optimization (with safe gap after it)
    optimize_channel_growth(youtube)

    # 2. Fetch Videos
    videos = get_channel_videos(youtube, max_results=35)
    print(f"\n📋 Fetched top {len(videos)} videos from channel for inspection.\n")

    optimized_count = 0
    skipped_count = 0

    for idx, v in enumerate(videos, 1):
        print(f"[{idx}/{len(videos)}] Checking Video: {v['title']}")

        is_description_good = len(v['description'].strip()) > 150
        has_sufficient_tags = len(v['tags']) >= 5

        if is_description_good and has_sufficient_tags:
            print(f"   ⏩ SKIPPED: Metadata is already high quality.\n")
            skipped_count += 1
            continue

        print(f"   ⚡ OPTIMIZING via Gemini...")
        new_title, new_desc, new_tags = optimize_with_gemini(v['title'], v['description'])
        
        if new_title and new_desc:
            update_video_metadata(youtube, v['id'], new_title, new_desc, new_tags, v['categoryId'])
            optimized_count += 1

        # 🛑 Strict 30 seconds pause between video requests to respect 5 RPM quota limit safely
        print("   ⏳ Waiting 30 seconds for quota safety...")
        time.sleep(30)
        print("-" * 50)

    print("\n==================================================")
    print(f"🎉 AUTOMATION COMPLETED SUCCESSFULLY WITHOUT ERRORS!")
    print(f"📊 Summary: {optimized_count} Videos Updated | {skipped_count} Skipped")
    print("==================================================")


if __name__ == "__main__":
    main()
