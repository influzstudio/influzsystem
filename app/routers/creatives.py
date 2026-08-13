from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import json

from app.database import get_db
from app.models import Client, SocialPost, AdminUser

router = APIRouter(prefix="/clients/{client_id}/creatives", tags=["creatives"])

from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["fromjson"] = json.loads


def require_admin(request, db):
    uid = request.session.get("admin_id")
    if not uid: return RedirectResponse("/login", status_code=303)
    return db.query(AdminUser).filter(AdminUser.id == uid).first()


@router.get("", response_class=HTMLResponse)
def creatives_page(request: Request, client_id: int, db: Session = Depends(get_db)):
    admin = require_admin(request, db)
    if isinstance(admin, RedirectResponse): return admin
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client: raise HTTPException(404)
    posts = db.query(SocialPost).filter(
        SocialPost.client_id == client_id,
        SocialPost.status.in_(["approved", "creative_ready", "creative_approved", "posted"])
    ).order_by(SocialPost.post_date).all()
    return templates.TemplateResponse("admin/creatives.html", {
        "request": request, "admin": admin, "client": client, "posts": posts,
    })


@router.post("/{post_id}/generate")
def generate_creative(request: Request, client_id: int, post_id: int, db: Session = Depends(get_db)):
    admin = require_admin(request, db)
    if isinstance(admin, RedirectResponse): return admin
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post: raise HTTPException(404)
    client = db.query(Client).filter(Client.id == client_id).first()

    try:
        from app.services.creative_service import generate_creative as gen_fn, generate_carousel as gen_carousel_fn
        photo_keywords = []
        if post.reference_note:
            photo_keywords.append(post.reference_note)
        photo_keywords.append(post.topic)  # raw topic first — "Paris Weekend Vacation", not diluted with business category words
        photo_keywords.append(f"{post.topic} {client.industry}" if client else post.topic)
        if client and client.products:
            photo_keywords.append(f"{client.products[0]} {client.industry}")
        if client and client.services:
            photo_keywords.append(f"{client.services[0]} {client.industry}")
        photo_keywords.append(client.industry if client else "")

        common_kwargs = dict(
            post_id=post.id,
            post_type=post.post_type,
            topic=post.topic,
            niche=client.industry if client else "",
            business_name=client.business_name if client else "Client",
            website=client.website_url.replace("https://","").replace("http://","").rstrip("/") if client and client.website_url else "",
            brand_colors=client.brand_colors if client else None,
            logo_path=client.logo_path if client else "",
            photo_keywords=photo_keywords,
        )

        if post.post_type.lower() == "carousel":
            paths = gen_carousel_fn(
                slides=post.carousel_slides or [],
                caption=post.caption or "",
                **common_kwargs,
            )
            post.creative_paths = paths
            post.creative_path = paths[0] if paths else ""
        else:
            path = gen_fn(
                cover_text=post.cover_text or post.topic,
                image_text=post.image_text or "",
                **common_kwargs,
            )
            post.creative_path = path
            post.creative_paths = [path]

        post.status = "creative_ready"
        db.commit()
    except Exception as e:
        print(f"Creative error: {e}")

    return RedirectResponse(f"/clients/{client_id}/creatives", status_code=303)


@router.post("/{post_id}/approve-creative")
def approve_creative(request: Request, client_id: int, post_id: int, db: Session = Depends(get_db)):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post: raise HTTPException(404)
    post.status = "creative_approved"
    db.commit()
    return RedirectResponse(f"/clients/{client_id}/creatives", status_code=303)


@router.post("/{post_id}/reject-creative")
def reject_creative(request: Request, client_id: int, post_id: int, db: Session = Depends(get_db)):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post: raise HTTPException(404)
    post.status = "approved"
    post.creative_path = ""
    post.creative_paths = []
    db.commit()
    return RedirectResponse(f"/clients/{client_id}/creatives", status_code=303)


@router.post("/{post_id}/publish")
def publish_post(request: Request, client_id: int, post_id: int, db: Session = Depends(get_db)):
    from datetime import date
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post: raise HTTPException(404)
    post.status = "posted"
    post.posted_at = date.today()
    db.commit()
    return RedirectResponse(f"/clients/{client_id}/creatives", status_code=303)


@router.get("/image/{post_id}")
def serve_creative(post_id: int):
    path = Path(f"/tmp/creatives/post_{post_id}.png")
    if path.exists():
        return FileResponse(str(path), media_type="image/png")
    raise HTTPException(404)


@router.get("/image/{post_id}/{slide}")
def serve_creative_slide(post_id: int, slide: int):
    path = Path(f"/tmp/creatives/post_{post_id}_s{slide}.png")
    if path.exists():
        return FileResponse(str(path), media_type="image/png")
    raise HTTPException(404)
