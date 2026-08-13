from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class SocialPost(Base):
    __tablename__ = "social_posts"

    id              = Column(Integer, primary_key=True)
    client_id       = Column(Integer, ForeignKey("clients.id"), nullable=False)
    post_date       = Column(Date, nullable=False)
    platforms       = Column(JSON, default=[])          # ["instagram", "facebook"]
    post_type       = Column(String, default="Static")  # Static, Reel, Carousel, Story, UGC, Short, Long
    topic           = Column(String, default="")
    cover_text      = Column(String, default="")
    image_text      = Column(String, default="")
    caption         = Column(Text, default="")
    hashtags        = Column(JSON, default=[])
    reference_note  = Column(Text, default="")
    script_outline  = Column(Text, default="")          # for YT videos
    thumbnail_text  = Column(String, default="")        # for YT
    tags            = Column(JSON, default=[])          # for YT SEO
    language        = Column(String, default="english")
    content_angle   = Column(String, default="")
    audience_segment= Column(String, default="")        # which segment this targets
    goal            = Column(String, default="awareness") # awareness, leads, engagement, sales
    carousel_slides = Column(JSON, default=[])           # [{"slide_headline":..,"slide_subtext":..}, ...] for Carousel posts
    creative_path   = Column(String, default="")        # generated image path (slide 1 / cover, for back-compat)
    creative_paths  = Column(JSON, default=[])           # full ordered list of slide image paths
    video_path      = Column(String, default="")        # generated video path
    thumbnail_path  = Column(String, default="")
    status          = Column(String, default="draft")   # draft, approved, scheduled, posted, failed
    platform_post_id= Column(String, default="")        # ID after posting
    client_feedback = Column(Text, default="")
    is_on_demand    = Column(Boolean, default=False)
    posted_at       = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    client    = relationship("Client", back_populates="social_posts")
    analytics = relationship("SocialAnalytics", back_populates="post", cascade="all, delete-orphan")


class SocialAnalytics(Base):
    __tablename__ = "social_analytics"

    id           = Column(Integer, primary_key=True)
    post_id      = Column(Integer, ForeignKey("social_posts.id"), nullable=False)
    platform     = Column(String, default="")
    impressions  = Column(Integer, default=0)
    reach        = Column(Integer, default=0)
    likes        = Column(Integer, default=0)
    comments     = Column(Integer, default=0)
    shares       = Column(Integer, default=0)
    saves        = Column(Integer, default=0)
    clicks       = Column(Integer, default=0)
    video_views  = Column(Integer, default=0)
    watch_time   = Column(Float, default=0.0)
    fetched_at   = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("SocialPost", back_populates="analytics")
