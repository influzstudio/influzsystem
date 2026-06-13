from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import json

from app.database import SessionLocal, engine, Base
from app.models.client import Client, ContentItem
from app.services.ai_content import generate_content_calendar

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Influz Studio - System")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["fromjson"] = json.loads


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    clients = db.query(Client).order_by(Client.created_at.desc()).all()
    return templates.TemplateResponse(
        "index.html", {"request": request, "clients": clients}
    )


@app.get("/onboard", response_class=HTMLResponse)
def onboard_form(request: Request):
    return templates.TemplateResponse("onboard.html", {"request": request})


@app.post("/onboard")
def onboard_submit(
    request: Request,
    business_name: str = Form(...),
    niche: str = Form(...),
    brand_voice: str = Form(...),
    goals: str = Form(...),
    instagram_handle: str = Form(""),
    facebook_page: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    client = Client(
        business_name=business_name,
        niche=niche,
        brand_voice=brand_voice,
        goals=goals,
        instagram_handle=instagram_handle,
        facebook_page=facebook_page,
        notes=notes,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return RedirectResponse(url=f"/client/{client.id}", status_code=303)


@app.get("/client/{client_id}", response_class=HTMLResponse)
def client_detail(request: Request, client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    content_items = (
        db.query(ContentItem)
        .filter(ContentItem.client_id == client_id)
        .order_by(ContentItem.day_index)
        .all()
    )
    return templates.TemplateResponse(
        "client_detail.html",
        {"request": request, "client": client, "content_items": content_items},
    )


@app.post("/client/{client_id}/generate")
def generate_calendar(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Clear existing generated (unapproved) items for regeneration
    db.query(ContentItem).filter(
        ContentItem.client_id == client_id, ContentItem.status == "generated"
    ).delete()
    db.commit()

    items = generate_content_calendar(
        business_name=client.business_name,
        niche=client.niche,
        brand_voice=client.brand_voice,
        goals=client.goals,
    )

    for idx, item in enumerate(items):
        content_item = ContentItem(
            client_id=client.id,
            day_index=idx,
            day_label=item.get("day", f"Day {idx+1}"),
            post_type=item.get("type", "Post"),
            theme=item.get("theme", ""),
            caption=item.get("caption", ""),
            hashtags=json.dumps(item.get("hashtags", [])),
            status="generated",
        )
        db.add(content_item)
    db.commit()

    return RedirectResponse(url=f"/client/{client_id}", status_code=303)


@app.post("/content/{item_id}/approve")
def approve_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.status = "approved"
    db.commit()
    return RedirectResponse(url=f"/client/{item.client_id}", status_code=303)


@app.post("/content/{item_id}/update")
def update_item(
    item_id: int,
    caption: str = Form(...),
    db: Session = Depends(get_db),
):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.caption = caption
    db.commit()
    return RedirectResponse(url=f"/client/{item.client_id}", status_code=303)


@app.get("/client/{client_id}/analytics", response_class=HTMLResponse)
def analytics(request: Request, client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    # Placeholder analytics data - will be replaced with live Meta API data
    sample_data = {
        "followers": 4820,
        "followers_growth": "+6.2%",
        "avg_reach": 2310,
        "reach_growth": "+11.4%",
        "engagement_rate": "4.8%",
        "engagement_growth": "+0.7pt",
        "posts_published": 12,
        "weekly_reach": [1450, 1820, 2090, 2310],
        "weekly_engagement": [58, 79, 95, 112],
    }
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "client": client, "data": sample_data},
    )
