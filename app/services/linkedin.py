"""
LinkedIn OAuth and publishing service.
Uses UGC Posts API which works with Default Tier apps.
"""
import os
import httpx
from urllib.parse import urlencode

CLIENT_ID     = os.getenv("LINKEDIN_CLIENT_ID", "78k04m3ta0euvx")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI  = os.getenv("LINKEDIN_REDIRECT_URI",
                           "https://influzsystem.onrender.com/auth/linkedin/callback")

SCOPES = "openid profile w_member_social"

AUTH_URL    = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL   = "https://www.linkedin.com/oauth/v2/accessToken"
PROFILE_URL = "https://api.linkedin.com/v2/userinfo"
UGC_POSTS_URL = "https://api.linkedin.com/v2/ugcPosts"
ASSETS_URL    = "https://api.linkedin.com/v2/assets?action=registerUpload"


def get_auth_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": SCOPES,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    with httpx.Client() as client:
        resp = client.post(TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        })
        resp.raise_for_status()
        return resp.json()


def get_linkedin_profile(access_token: str) -> dict:
    try:
        with httpx.Client() as client:
            resp = client.get(
                PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            data = resp.json()
            return {
                "sub": data.get("sub", ""),
                "name": data.get("name", "Influz Studio"),
            }
    except Exception:
        return {"sub": "", "name": "Connected"}


def _upload_image_asset(access_token: str, person_urn: str, image_path: str) -> str:
    """Upload image using v2/assets API (works with Default Tier)."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": f"urn:li:person:{person_urn}",
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }
    with httpx.Client(timeout=30) as client:
        reg_resp = client.post(ASSETS_URL, headers=headers, json=register_payload)
        reg_resp.raise_for_status()
        reg_data = reg_resp.json()
        upload_url = reg_data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset = reg_data["value"]["asset"]

        with open(image_path, "rb") as f:
            img_bytes = f.read()
        client.put(
            upload_url,
            content=img_bytes,
            headers={"Authorization": f"Bearer {access_token}",
                     "Content-Type": "application/octet-stream"},
        )
    return asset


def post_to_linkedin(
    access_token: str,
    person_urn: str,
    caption: str,
    image_paths: list[str] | None = None,
) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    author = f"urn:li:person:{person_urn}"

    if not image_paths:
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    else:
        media = []
        for path in image_paths[:1]:  # single image for now
            try:
                asset = _upload_image_asset(access_token, person_urn, path)
                media.append({
                    "status": "READY",
                    "media": asset,
                    "title": {"text": caption[:100]},
                })
            except Exception:
                pass

        if media:
            payload = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": caption},
                        "shareMediaCategory": "IMAGE",
                        "media": media,
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        else:
            # fallback text only
            payload = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": caption},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

    with httpx.Client(timeout=30) as client:
        resp = client.post(UGC_POSTS_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return {"status": "posted", "post_id": resp.headers.get("x-restli-id", "")}
