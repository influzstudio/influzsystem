from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    niche = Column(String, nullable=False)
    brand_voice = Column(String, nullable=False)
    goals = Column(Text, nullable=False)
    city = Column(String, default="")
    instagram_handle = Column(String, default="")
    facebook_page = Column(String, default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Package & pricing
    posts_per_month = Column(Integer, default=16)
    rate_story = Column(Float, default=150.0)
    rate_post = Column(Float, default=300.0)
    rate_carousel = Column(Float, default=500.0)
    rate_reel = Column(Float, default=800.0)
    rate_ugc = Column(Float, default=600.0)
    rate_on_demand = Column(Float, default=1000.0)

    content_items = relationship(
        "ContentItem", back_populates="client", cascade="all, delete-orphan"
    )


class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    post_date = Column(Date, nullable=False)
    post_type = Column(String, default="Static")  # Static, Reel, Carousel, Story, UGC
    platforms = Column(Text, default="[]")
    topic = Column(String, default="")          # Creative angle
    cover_text = Column(String, default="")     # Headline text on image
    image_text = Column(String, default="")     # Supporting visual copy
    caption = Column(Text, default="")          # Full ready-to-post caption + hashtags
    hashtags = Column(Text, default="[]")       # Legacy field kept for compat
    reference_note = Column(Text, default="")   # Visual reference direction
    client_feedback = Column(Text, default="")  # Space for client notes
    client_photo_path = Column(String, default="")  # Path to client-uploaded photo
    status = Column(String, default="generated")  # generated, approved, scheduled, posted
    is_on_demand = Column(Boolean, default=False)
    creative_paths = Column(Text, default="[]")   # JSON list of generated PNG paths
    posted_at = Column(String, default="")         # ISO date when posted
    posted_to = Column(Text, default="[]")         # JSON list of platforms posted to
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="content_items")


class LinkedInToken(Base):
    """Stores LinkedIn OAuth tokens per client."""
    __tablename__ = "linkedin_tokens"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), unique=True, nullable=False)
    access_token = Column(Text, nullable=False)
    person_urn = Column(String, nullable=False)  # LinkedIn sub / person ID
    name = Column(String, default="")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
