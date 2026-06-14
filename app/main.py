from datetime import date, datetime
import json

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.client import Client, ContentItem, PricingRate
from app.services.ai_content import generate_content_calendar
from app.services.pricing import (
    ensure_default_rates,
    get_rates_map,
    calculate_item_cost,
    calculate_calendar_cost,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Influz Studio - System")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["fromjson"] = json.loads


def get_db():
    db = SessionLocal()
    try:
        ensure_default_rates(db)
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
        .order_by(ContentItem.post_date)
        .all()
    )

    rates = get_rates_map(db)
    cost_summary = calculate_calendar_cost(content_items, rates)

    # Build per-item cost for display
    item_costs = {}
    for item in content_items:
        platforms = json.loads(item.platforms or "[]")
        item_costs[item.id] = calculate_item_cost(item.post_type, platforms, rates)

    # Build calendar grid: group items by month, then by date
    months = build_calendar_months(content_items)

    return templates.TemplateResponse(
        "client_detail.html",
        {
            "request": request,
            "client": client,
            "content_items": content_items,
            "months": months,
            "cost_summary": cost_summary,
            "item_costs": item_costs,
            "rates": rates,
            "post_types": ["Story", "Post", "Carousel", "Reel"],
            "today": date.today().isoformat(),
        },
    )


def build_calendar_months(content_items: list[ContentItem]):
    """Group content items into a month-grid structure for calendar display.

    Returns a list of month dicts: {label, weeks: [[day_cell,...], ...]}
    where each day_cell is {date, items} or None for padding cells.
    """
    if not content_items:
        return []

    items_by_date = {}
    for item in content_items:
        items_by_date.setdefault(item.post_date, []).append(item)

    start = min(items_by_date.keys())
    end = max(items_by_date.keys())

    # Build list of (year, month) spanned
    months = []
    cursor = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while cursor <= end_month:
        months.append((cursor.year, cursor.month))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    month_data = []
    for year, month in months:
        first_day = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        days_in_month = (next_month - first_day).days

        # Monday-first grid: weekday() Mon=0..Sun=6
        leading_blanks = first_day.weekday()

        weeks = []
        week = [None] * leading_blanks
        for day_num in range(1, days_in_month + 1):
            current = date(year, month, day_num)
            cell = {
                "date": current,
                "posts": items_by_date.get(current, []),
            }
            week.append(cell)
            if len(week) == 7:
                weeks.append(week)
                week = []
        if week:
            while len(week) < 7:
                week.append(None)
            weeks.append(week)

        month_data.append({
            "label": first_day.strftime("%B %Y"),
            "weeks": weeks,
        })

    return month_data


@app.post("/client/{client_id}/generate")
def generate_calendar(
    client_id: int,
    start_date: str = Form(None),
    num_days: int = Form(60),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Clear existing non-approved items before regenerating
    db.query(ContentItem).filter(
        ContentItem.client_id == client_id, ContentItem.status == "generated"
    ).delete()
    db.commit()

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today()

    items = generate_content_calendar(
        business_name=client.business_name,
        niche=client.niche,
        brand_voice=client.brand_voice,
        goals=client.goals,
        start_date=start,
        num_days=num_days,
    )

    for item in items:
        content_item = ContentItem(
            client_id=client.id,
            post_date=datetime.strptime(item["post_date"], "%Y-%m-%d").date(),
            post_type=item.get("post_type", "Post"),
            platforms=json.dumps(item.get("platforms", ["instagram"])),
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
    return RedirectResponse(url=f"/client/{item.client_id}#post-{item_id}", status_code=303)


@app.post("/content/{item_id}/update")
def update_item(
    item_id: int,
    caption: str = Form(...),
    post_type: str = Form(...),
    platforms: list[str] = Form([]),
    post_date: str = Form(...),
    db: Session = Depends(get_db),
):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.caption = caption
    item.post_type = post_type
    item.platforms = json.dumps(platforms)
    item.post_date = datetime.strptime(post_date, "%Y-%m-%d").date()
    db.commit()
    return RedirectResponse(url=f"/client/{item.client_id}#post-{item_id}", status_code=303)


@app.get("/client/{client_id}/analytics", response_class=HTMLResponse)
def analytics(request: Request, client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
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


@app.get("/settings/pricing", response_class=HTMLResponse)
def pricing_settings(request: Request, db: Session = Depends(get_db)):
    rates = db.query(PricingRate).all()
    return templates.TemplateResponse(
        "pricing_settings.html", {"request": request, "rates": rates}
    )


@app.post("/settings/pricing/update")
async def update_pricing_rates(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    rates = db.query(PricingRate).all()
    for rate in rates:
        key = f"rate_{rate.post_type}"
        if key in form:
            try:
                rate.rate_per_platform = float(form[key])
            except ValueError:
                pass
    db.commit()
    return RedirectResponse(url="/settings/pricing", status_code=303)
