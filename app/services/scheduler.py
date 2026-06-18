"""
Background scheduler — runs daily jobs:
1. Generate creatives for approved posts due in the next 24 hours
2. Publish creative_approved posts that are due today
"""
import os
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models.client import Client, ContentItem

log = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def generate_due_creatives():
    """Find approved posts due today or tomorrow → generate their creatives."""
    from app.services.creative import (
        generate_static_creative, generate_carousel_creatives
    )
    db = SessionLocal()
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        items = (
            db.query(ContentItem)
            .filter(
                ContentItem.status == "approved",
                ContentItem.post_date.in_([today, tomorrow]),
            )
            .all()
        )
        for item in items:
            try:
                if item.post_type == "Carousel":
                    paths = generate_carousel_creatives(
                        item.id, item.cover_text or item.topic,
                        item.image_text or item.topic, item.post_type
                    )
                    item.creative_paths = json.dumps(paths)
                else:
                    path = generate_static_creative(
                        item.id, item.cover_text or item.topic,
                        item.image_text or "", item.post_type, item.topic
                    )
                    item.creative_paths = json.dumps([path])

                item.status = "creative_ready"
                log.info(f"Creative generated for item {item.id}: {item.topic}")
            except Exception as e:
                log.error(f"Creative generation failed for item {item.id}: {e}")
        db.commit()
    finally:
        db.close()


def publish_due_posts():
    """Find creative_approved posts due today → post to LinkedIn."""
    from app.services.linkedin import post_to_linkedin
    db = SessionLocal()
    try:
        today = date.today()
        items = (
            db.query(ContentItem)
            .filter(
                ContentItem.status == "creative_approved",
                ContentItem.post_date == today,
            )
            .all()
        )
        for item in items:
            client = db.query(Client).filter(Client.id == item.client_id).first()
            if not client:
                continue

            platforms = json.loads(item.platforms or "[]")
            creative_paths = json.loads(item.creative_paths or "[]")
            full_paths = [
                str(Path("app/static") / p) for p in creative_paths
                if Path(f"app/static/{p}").exists()
            ]

            posted_to = []

            if "linkedin" in platforms and client.linkedin_access_token:
                try:
                    result = post_to_linkedin(
                        access_token=client.linkedin_access_token,
                        person_urn=client.linkedin_person_urn,
                        caption=item.caption,
                        image_paths=full_paths or None,
                    )
                    posted_to.append("linkedin")
                    log.info(f"Posted item {item.id} to LinkedIn: {result}")
                except Exception as e:
                    log.error(f"LinkedIn post failed for item {item.id}: {e}")

            if posted_to:
                item.status = "posted"
                item.posted_at = date.today().isoformat()
                item.posted_to = json.dumps(posted_to)
                log.info(f"Item {item.id} marked as posted to: {posted_to}")

        db.commit()
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler. Called once on app startup."""
    # Generate creatives at 8 AM IST daily
    scheduler.add_job(
        generate_due_creatives,
        CronTrigger(hour=8, minute=0, timezone="Asia/Kolkata"),
        id="generate_creatives",
        replace_existing=True,
    )
    # Publish posts at 10 AM IST daily
    scheduler.add_job(
        publish_due_posts,
        CronTrigger(hour=10, minute=0, timezone="Asia/Kolkata"),
        id="publish_posts",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()
        log.info("Influz Studio scheduler started — creatives at 8 AM, publishing at 10 AM IST")
