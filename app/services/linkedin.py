"""
LinkedIn OAuth and publishing service.
"""
import os
import httpx
from urllib.parse import urlencode

CLIENT_ID     = os.getenv("LINKEDIN_CLIENT_ID", "78k04m3ta0euvx")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI  = os.getenv("LINKEDIN_REDIRECT_URI",
                           "https://influzsystem.onrender.com/auth/linkedin/callback")

SCOPES = "r_liteprofile r_emailaddress w_member_social"

AUTH_URL    = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL   = "https://www.linkedin.com/oauth/v2/accessToken"
PROFILE_URL = "https://api.linkedin.com/v2/me"
POSTS_URL   = "https://api.linkedin.com/rest/posts"
IMAGES_URL  = "https://api.linkedin.com/rest/images?action=initializeUpload"


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
    """Get profile using r_liteprofile scope."""
    with httpx.Client() as client:
        resp = client.get(
            PROFILE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            }
        )
        resp.raise_for_status()
        data = resp.json()
        person_id = data.get("id", "")
        first = data.get("localizedFirstName", "")
        last = data.get("localizedLastName", "")
        return {
            "sub": person_id,
            "name": f"{first} {last}".strip(),
        }


def _upload_image(access_token: str, person_urn: str, image_path: str) -> str:
    """Upload an image to LinkedIn and return the image URN."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202501",
    }
    with httpx.Client() as client:
        init_resp = client.post(IMAGES_URL, headers=headers, json={
            "initializeUploadRequest": {
                "owner": f"urn:li:person:{person_urn}"
            }
        })
        init_resp.raise_for_status()
        upload_data = init_resp.json()["value"]
        upload_url = upload_data["uploadUrl"]
        image_urn = upload_data["image"]

        with open(image_path, "rb") as f:
            img_bytes = f.read()
        put_resp = client.put(
            upload_url,
            content=img_bytes,
            headers={"Authorization": f"Bearer {access_token}",
                     "Content-Type": "application/octet-stream"},
        )
        put_resp.raise_for_status()
    return image_urn


def post_to_linkedin(
    access_token: str,
    person_urn: str,
    caption: str,
    image_paths: list[str] | None = None,
) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202501",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    author = f"urn:li:person:{person_urn}"

    if not image_paths:
        payload = {
            "author": author,
            "commentary": caption,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
    elif len(image_paths) == 1:
        image_urn = _upload_image(access_token, person_urn, image_paths[0])
        payload = {
            "author": author,
            "commentary": caption,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "media": {
                    "altText": caption[:200],
                    "id": image_urn,
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
    else:
        image_urns = [_upload_image(access_token, person_urn, p) for p in image_paths]
        payload = {
            "author": author,
            "commentary": caption,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "multiImage": {
                    "images": [
                        {"altText": f"Slide {i+1}", "id": urn}
                        for i, urn in enumerate(image_urns)
                    ]
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

    with httpx.Client() as client:
        resp = client.post(POSTS_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return {"status": "posted", "post_id": resp.headers.get("x-restli-id", "")}
