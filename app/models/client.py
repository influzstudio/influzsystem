from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Float, ForeignKey
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

    content_items = relationship(
        "ContentItem", back_populates="client", cascade="all, delete-orphan"
    )


class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    post_date = Column(Date, nullable=False)
    post_type = Column(String, default="Post")  # Story, Post, Carousel, Reel
    platforms = Column(Text, default="[]")  # JSON list e.g. ["instagram","facebook"]
    theme = Column(String, default="")
    caption = Column(Text, default="")
    hashtags = Column(Text, default="[]")
    status = Column(String, default="generated")  # generated, approved, scheduled, posted
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="content_items")


class PricingRate(Base):
    """Global default rates per post type, per platform. Single row per post_type."""
    __tablename__ = "pricing_rates"

    id = Column(Integer, primary_key=True, index=True)
    post_type = Column(String, unique=True, nullable=False)  # Story, Post, Carousel, Reel
    rate_per_platform = Column(Float, nullable=False)
