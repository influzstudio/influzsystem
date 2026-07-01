"""
YouTube OAuth and content management service.
Uses YouTube Data API v3 for channel stats and video management.
"""
import os
import json
import httpx
from urllib.parse import urlencode

YT_CLIENT_ID     = os.getenv("YOUTUBE_CLIENT_ID", "710069384292-nrme0b4v6bgh7f22ffmacjmt0ahvc5es.apps.googleusercontent.com")
YT_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YT_REDIRECT_URI  = os.getenv("YOUTUBE_REDIRECT_URI", "https://influzsystem.onrender.com/auth/youtube/callback")

SCOPES = "https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.upload"

AUTH_URL    = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL   = "https://oauth2.googleapis.com/token"
CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"
VIDEOS_URL  = "https://www.googleapis.com/youtube/v3/videos"
SEARCH_URL  = "https://www.googleapis.com/youtube/v3/search"


def get_auth_url(state: str) -> str:
    params = {
        "client_id": YT_CLIENT_ID,
        "redirect_uri": YT_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    with httpx.Client() as client:
        resp = client.post(TOKEN_URL, data={
            "code": code,
            "client_id": YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SECRET,
            "redirect_uri": YT_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    with httpx.Client() as client:
        resp = client.post(TOKEN_URL, data={
            "refresh_token": refresh_token,
            "client_id": YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SECRET,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        return resp.json()


def get_channel_stats(access_token: str) -> dict:
    """Get channel stats — subscribers, views, video count."""
    with httpx.Client() as client:
        resp = client.get(CHANNEL_URL, params={
            "part": "snippet,statistics",
            "mine": "true",
        }, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        data = resp.json()
        if not data.get("items"):
            return {}
        item = data["items"][0]
        stats = item["statistics"]
        snippet = item["snippet"]
        return {
            "channel_id": item["id"],
            "channel_name": snippet["title"],
            "description": snippet.get("description", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "subscribers": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
        }


def get_recent_videos(access_token: str, channel_id: str, max_results: int = 10) -> list[dict]:
    """Get recent videos with their stats."""
    with httpx.Client() as client:
        # Get video IDs
        search_resp = client.get(SEARCH_URL, params={
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "maxResults": max_results,
            "type": "video",
        }, headers={"Authorization": f"Bearer {access_token}"})
        search_resp.raise_for_status()
        items = search_resp.json().get("items", [])
        if not items:
            return []
        video_ids = ",".join(i["id"]["videoId"] for i in items)

        # Get video stats
        stats_resp = client.get(VIDEOS_URL, params={
            "part": "snippet,statistics,contentDetails",
            "id": video_ids,
        }, headers={"Authorization": f"Bearer {access_token}"})
        stats_resp.raise_for_status()
        videos = []
        for v in stats_resp.json().get("items", []):
            s = v.get("statistics", {})
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "published": v["snippet"]["publishedAt"][:10],
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
                "thumbnail": v["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
            })
        return videos
