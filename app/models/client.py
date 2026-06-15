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
    instagram_handle = Column(String, default="")
    facebook_page = Column(String, default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Package & pricing - set during onboarding, not edited from calendar view
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
    post_type = Column(String, default="Post")  # Story, Post, Carousel, Reel, UGC
    platforms = Column(Text, default="[]")  # JSON list e.g. ["instagram","facebook"]
    theme = Column(String, default="")
    caption = Column(Text, default="")
    hashtags = Column(Text, default="[]")
    status = Column(String, default="generated")  # generated, approved, scheduled, posted
    is_on_demand = Column(Boolean, default=False)  # True = festival/special add-on post, flat rate
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="content_items")
