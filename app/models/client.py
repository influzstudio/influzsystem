from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class Client(Base):
    __tablename__ = "clients"

    id            = Column(Integer, primary_key=True)
    slug          = Column(String, unique=True, nullable=False)  # url-safe name
    business_name = Column(String, nullable=False)
    industry      = Column(String, default="")         # travel, retail, finance, etc.
    website_url   = Column(String, default="")
    logo_path     = Column(String, default="")
    brand_colors  = Column(JSON, default={"primary": "#2DD4BF", "secondary": "#0E1822"})
    brand_voice   = Column(Text, default="")
    usp           = Column(Text, default="")           # unique selling proposition
    goals         = Column(JSON, default=[])           # ["leads", "awareness", "sales"]
    city          = Column(String, default="")
    country       = Column(String, default="India")

    # Deeper onboarding data — feeds AI content generation & creative branding
    services        = Column(JSON, default=[])         # ["Interior Design", "Space Planning", ...]
    products        = Column(JSON, default=[])         # specific products/packages to feature
    target_audience = Column(Text, default="")          # who they sell to — demographics, psychographics
    price_range     = Column(String, default="")        # "Budget", "Mid-range", "Premium", "₹5k-50k", etc.
    content_pillars = Column(JSON, default=[])          # recurring themes e.g. ["Behind the scenes","Tips","Testimonials"]
    competitors     = Column(Text, default="")           # optional differentiation context
    instagram_handle= Column(String, default="")
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    audience_segments   = relationship("AudienceSegment", back_populates="client", cascade="all, delete-orphan")
    platforms           = relationship("Platform", back_populates="client", cascade="all, delete-orphan")
    social_posts        = relationship("SocialPost", back_populates="client", cascade="all, delete-orphan")
    seo_keywords        = relationship("SEOKeyword", back_populates="client", cascade="all, delete-orphan")
    seo_pages           = relationship("SEOPage", back_populates="client", cascade="all, delete-orphan")
    ad_campaigns        = relationship("AdCampaign", back_populates="client", cascade="all, delete-orphan")
    leads               = relationship("Lead", back_populates="client", cascade="all, delete-orphan")
    website_pages       = relationship("WebsitePage", back_populates="client", cascade="all, delete-orphan")
    monthly_reports     = relationship("MonthlyReport", back_populates="client", cascade="all, delete-orphan")
    tasks               = relationship("Task", back_populates="client", cascade="all, delete-orphan")
    users               = relationship("ClientUser", back_populates="client", cascade="all, delete-orphan")


class AudienceSegment(Base):
    __tablename__ = "audience_segments"

    id          = Column(Integer, primary_key=True)
    client_id   = Column(Integer, ForeignKey("clients.id"), nullable=False)
    name        = Column(String, nullable=False)       # "Honeymooners", "Budget Backpackers"
    description = Column(Text, default="")
    age_range   = Column(String, default="")
    interests   = Column(JSON, default=[])
    pain_points = Column(JSON, default=[])
    platforms   = Column(JSON, default=[])             # where they hang out
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="audience_segments")


class Platform(Base):
    __tablename__ = "platforms"

    id           = Column(Integer, primary_key=True)
    client_id    = Column(Integer, ForeignKey("clients.id"), nullable=False)
    platform     = Column(String, nullable=False)      # instagram, facebook, youtube, linkedin, gsc, ga4, meta_ads, google_ads
    access_token = Column(Text, default="")
    refresh_token= Column(Text, default="")
    account_id   = Column(String, default="")
    account_name = Column(String, default="")
    extra_data   = Column(JSON, default={})            # platform-specific data
    is_active    = Column(Boolean, default=True)
    connected_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="platforms")
