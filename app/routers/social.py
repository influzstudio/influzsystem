from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
import json

from app.database import get_db
from app.models import Client, SocialPost, AdminUser

router = APIRouter(prefix="/clients/{client_id}/social", tags=["social"])


def require_admin(request: Request, db: Session):
    user_id = request.session.get("admin_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    return db.query(AdminUser).filter(AdminUser.id == user_id).first()


from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["fromjson"] = json.loads


@router.get("", response_class=HTMLResponse)
def social_page(request: Request, client_id: int, db: Session = Depends(get_db)):
    admin = require_admin(request, db)
    if isinstance(admin, RedirectResponse): return admin
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client: raise HTTPException(404)
    posts = db.query(SocialPost).filter(SocialPost.client_id == client_id).order_by(SocialPost.post_date).all()
    return templates.TemplateResponse("admin/social.html", {
        "request": request, "admin": admin, "client": client,
        "posts": posts, "today": date.today().isoformat()
    })


@router.post("/generate")
def generate_social_calendar(
    request: Request, client_id: int,
    start_date: str = Form(None),
    num_posts: int = Form(16),
    db: Session = Depends(get_db),
):
    admin = require_admin(request, db)
    if isinstance(admin, RedirectResponse): return admin
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client: raise HTTPException(404)

    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today()

    # Clear existing drafts
    db.query(SocialPost).filter(SocialPost.client_id == client_id, SocialPost.status == "draft").delete()
    db.commit()

    try:
        from app.services.ai_content import generate_social_calendar as gen_fn
        items = gen_fn(
            business_name=client.business_name,
            niche=client.industry,
            brand_voice=client.brand_voice,
            goals=", ".join(client.goals or []),
            city=client.city or "",
            start_date=start,
            num_posts=num_posts,
            usp=client.usp or "",
            services=client.services or [],
            products=client.products or [],
            target_audience=client.target_audience or "",
            price_range=client.price_range or "",
            content_pillars=client.content_pillars or [],
            competitors=client.competitors or "",
        )
    except Exception as e:
        print(f"Generate error: {e}")
        from app.services.ai_content import _fallback
        items = _fallback(start, num_posts, client.business_name)

    for item in items:
        try:
            db.add(SocialPost(
                client_id=client_id,
                post_date=datetime.strptime(item["post_date"], "%Y-%m-%d").date(),
                post_type=item.get("post_type", "Static"),
                platforms=item.get("platforms", ["instagram"]),
                topic=item.get("topic", ""),
                cover_text=item.get("cover_text", ""),
                image_text=item.get("image_text", ""),
                caption=item.get("caption", ""),
                reference_note=item.get("reference_note", ""),
                content_angle=item.get("content_angle", ""),
                status="draft",
            ))
        except Exception as e:
            print(f"Post insert error: {e}")
    db.commit()
    return RedirectResponse(f"/clients/{client_id}/social", status_code=303)


@router.post("/{post_id}/approve")
def approve_post(request: Request, client_id: int, post_id: int, db: Session = Depends(get_db)):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post: raise HTTPException(404)
    post.status = "approved"
    db.commit()
    return RedirectResponse(f"/clients/{client_id}/social", status_code=303)


@router.post("/{post_id}/delete")
def delete_post(request: Request, client_id: int, post_id: int, db: Session = Depends(get_db)):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post: raise HTTPException(404)
    db.delete(post)
    db.commit()
    return RedirectResponse(f"/clients/{client_id}/social", status_code=303)


@router.post("/{post_id}/update")
def update_post(
    request: Request, client_id: int, post_id: int,
    post_date: str = Form(...),
    post_type: str = Form(...),
    platforms: list[str] = Form([]),
    topic: str = Form(""),
    cover_text: str = Form(""),
    image_text: str = Form(""),
    caption: str = Form(""),
    reference_note: str = Form(""),
    client_feedback: str = Form(""),
    db: Session = Depends(get_db),
):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post: raise HTTPException(404)
    post.post_date = datetime.strptime(post_date, "%Y-%m-%d").date()
    post.post_type = post_type
    post.platforms = platforms
    post.topic = topic
    post.cover_text = cover_text
    post.image_text = image_text
    post.caption = caption
    post.reference_note = reference_note
    post.client_feedback = client_feedback
    db.commit()
    return RedirectResponse(f"/clients/{client_id}/social", status_code=303)
