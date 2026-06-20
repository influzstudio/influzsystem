"""
Background scheduler:
1. 8 AM IST — generate creatives for posts due tomorrow
2. 9 AM IST — auto-post creative_approved posts due TODAY
"""
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models.client import ContentItem, LinkedInToken

log = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def _get_full_paths(item, db) -> list[str]:
    """Get creative file paths, regenerating if missing."""
    from app.services.creative import generate_static_creative, generate_carousel_creatives
    creative_paths = json.loads(item.creative_paths or "[]")
    full_paths = []
    for p in creative_paths:
        full = f"app/static/{p}"
        if not Path(full).exists():
            try:
                if item.post_type == "Carousel":
                    generate_carousel_creatives(item.id, item.cover_text or item.topic,
                                                item.image_text or item.topic, item.post_type)
                else:
                    generate_static_creative(item.id, item.cover_text or item.topic,
                                             item.image_text or "", item.post_type, item.topic)
            except Exception as e:
                log.error(f"Creative regen failed for item {item.id}: {e}")
        if Path(full).exists():
            full_paths.append(full)
    return full_paths


def generate_due_creatives():
    """8 AM — generate creatives for approved posts due tomorrow."""
    from app.services.creative import generate_static_creative, generate_carousel_creatives
    db = SessionLocal()
    try:
        tomorrow = date.today() + timedelta(days=1)
        items = db.query(ContentItem).filter(
            ContentItem.status == "approved",
            ContentItem.post_date == tomorrow,
        ).all()
        for item in items:
            try:
                if item.post_type == "Carousel":
                    paths = generate_carousel_creatives(
                        item.id, item.cover_text or item.topic,
                        item.image_text or item.topic, item.post_type)
                else:
                    paths = [generate_static_creative(
                        item.id, item.cover_text or item.topic,
                        item.image_text or "", item.post_type, item.topic)]
                item.creative_paths = json.dumps(paths)
                item.status = "creative_ready"
                log.info(f"Creative generated for item {item.id}")
            except Exception as e:
                log.error(f"Creative generation failed for item {item.id}: {e}")
        db.commit()
    finally:
        db.close()


def publish_due_posts():
    """9 AM — publish creative_approved posts due TODAY on their scheduled date."""
    from app.services.linkedin import post_to_linkedin
    db = SessionLocal()
    try:
        today = date.today()
        items = db.query(ContentItem).filter(
            ContentItem.status == "creative_approved",
            ContentItem.post_date == today,
        ).all()

        for item in items:
            li_token = db.query(LinkedInToken).filter(
                LinkedInToken.client_id == item.client_id).first()
            if not li_token:
                log.warning(f"No LinkedIn token for client {item.client_id}")
                continue

            platforms = json.loads(item.platforms or "[]")
            full_paths = _get_full_paths(item, db)
            posted_to = []

            if "linkedin" in platforms:
                try:
                    try:
                        post_to_linkedin(
                            access_token=li_token.access_token,
                            person_urn=li_token.person_urn,
                            caption=item.caption,
                            image_paths=full_paths or None,
                        )
                    except Exception:
                        post_to_linkedin(
                            access_token=li_token.access_token,
                            person_urn=li_token.person_urn,
                            caption=item.caption,
                            image_paths=None,
                        )
                    posted_to.append("linkedin")
                    log.info(f"Posted item {item.id} to LinkedIn")
                except Exception as e:
                    log.error(f"LinkedIn post failed for item {item.id}: {e}")

            if posted_to:
                item.status = "posted"
                item.posted_at = today.isoformat()
                item.posted_to = json.dumps(posted_to)

        db.commit()
    finally:
        db.close()


def start_scheduler():
    # 8 AM IST — generate creatives for tomorrow's posts
    scheduler.add_job(generate_due_creatives,
                      CronTrigger(hour=8, minute=0, timezone="Asia/Kolkata"),
                      id="generate_creatives", replace_existing=True)
    # 9 AM IST — publish today's approved posts
    scheduler.add_job(publish_due_posts,
                      CronTrigger(hour=9, minute=0, timezone="Asia/Kolkata"),
                      id="publish_posts", replace_existing=True)
    if not scheduler.running:
        scheduler.start()
        log.info("Scheduler started — creatives at 8 AM, publishing at 9 AM IST")
