"""SQLAlchemy ORM models for the AI SDR system."""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum, Float
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()

# ── Enums ───────────────────────────────────────────────────

class LeadStatus(str, enum.Enum):
    NEW = "new"
    RESEARCHED = "researched"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"

class OutreachStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    NOT_INTERESTED = "not_interested"

class CRMStatus(str, enum.Enum):
    LEAD = "lead"
    QUALIFIED = "qualified"
    EMAIL_SENT = "email_sent"
    OPENED = "opened"
    CLICKED = "clicked"
    INTERESTED = "interested"
    MEETING_REQUESTED = "meeting_requested"
    TRIAL_STARTED = "trial_started"
    CUSTOMER = "customer"
    LOST = "lost"

class CampaignStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class ReplyCategory(str, enum.Enum):
    INTERESTED = "interested"
    QUESTION = "question"
    NOT_INTERESTED = "not_interested"
    SPAM = "spam"
    OOO = "ooo"
    FORWARDED = "forwarded"

class ContentType(str, enum.Enum):
    BLOG = "blog"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    WHATSAPP = "whatsapp"

# ── Models ──────────────────────────────────────────────────

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100))
    country = Column(String(100))
    city = Column(String(100))
    target_leads = Column(Integer, default=0)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.ACTIVE)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    leads = relationship("Lead", back_populates="campaign", lazy="selectin")


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    company = Column(String(255))
    website = Column(String(500))
    phone = Column(String(50))
    email = Column(String(255))
    facebook = Column(String(500))
    linkedin = Column(String(500))
    address = Column(Text)
    google_rating = Column(String(10))
    reviews = Column(Integer)
    category = Column(String(100))
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW)
    crm_status = Column(Enum(CRMStatus), default=CRMStatus.LEAD)
    ai_score = Column(Float, default=0.0)  # 0-100 qualification score
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    campaign = relationship("Campaign", back_populates="leads")
    research = relationship("LeadResearch", back_populates="lead", uselist=False, lazy="selectin")
    sequences = relationship("EmailSequence", back_populates="lead", lazy="selectin")
    email_logs = relationship("EmailLog", back_populates="lead", lazy="selectin")
    replies = relationship("Reply", back_populates="lead", lazy="selectin")
    followups = relationship("FollowUp", back_populates="lead", lazy="selectin")


class LeadResearch(Base):
    __tablename__ = "lead_research"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    website_live = Column(Boolean, default=False)
    has_contact_email = Column(Boolean, default=False)
    has_contact_form = Column(Boolean, default=False)
    has_whatsapp = Column(Boolean, default=False)
    has_facebook = Column(Boolean, default=False)
    has_instagram = Column(Boolean, default=False)
    has_blog = Column(Boolean, default=False)
    has_faq = Column(Boolean, default=False)
    has_about = Column(Boolean, default=False)
    has_services = Column(Boolean, default=False)
    website_summary = Column(Text)
    business_type = Column(String(255))
    pain_points = Column(JSON, default=list)
    has_live_chat = Column(Boolean, default=False)
    has_ai_chat = Column(Boolean, default=False)
    chat_tools = Column(JSON, default=list)
    qualified = Column(Boolean, default=False)
    qualification_reason = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="research")


class EmailSequence(Base):
    __tablename__ = "email_sequences"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    subject = Column(String(500))
    personalized_intro = Column(Text)
    pain_point = Column(Text)
    benefits = Column(Text)
    cta = Column(Text)
    email_body = Column(Text)
    linkedin_message = Column(Text)
    whatsapp_message = Column(Text)
    approved = Column(Boolean, default=False)
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="sequences")
    email_logs = relationship("EmailLog", back_populates="sequence", lazy="selectin")


class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    sequence_id = Column(Integer, ForeignKey("email_sequences.id"))
    status = Column(Enum(OutreachStatus), default=OutreachStatus.PENDING_APPROVAL)
    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    replied_at = Column(DateTime)
    bounced_at = Column(DateTime)
    smartlead_message_id = Column(String(255))
    followup_number = Column(Integer, default=0)  # 0 = initial, 1+ = follow-up
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="email_logs")
    sequence = relationship("EmailSequence", back_populates="email_logs")
    replies = relationship("Reply", back_populates="email_log", lazy="selectin")
    followups = relationship("FollowUp", back_populates="email_log", lazy="selectin")


class Reply(Base):
    __tablename__ = "replies"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    email_log_id = Column(Integer, ForeignKey("email_logs.id"))
    content = Column(Text)
    category = Column(Enum(ReplyCategory))
    sentiment_score = Column(Float, default=0.0)  # -1 to 1
    ai_draft_reply = Column(Text)
    approved = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="replies")
    email_log = relationship("EmailLog", back_populates="replies")


class FollowUp(Base):
    __tablename__ = "followups"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    email_log_id = Column(Integer, ForeignKey("email_logs.id"))
    followup_number = Column(Integer)  # 1, 2, 3
    scheduled_at = Column(DateTime)
    sent_at = Column(DateTime)
    status = Column(String(50), default="pending")  # pending, sent, stopped, replied
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="followups")
    email_log = relationship("EmailLog", back_populates="followups")


class DailyReport(Base):
    __tablename__ = "daily_reports"
    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, nullable=False)
    leads_found = Column(Integer, default=0)
    qualified = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    interested = Column(Integer, default=0)
    trials_started = Column(Integer, default=0)
    meetings_booked = Column(Integer, default=0)
    sent_to_telegram = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ContentPiece(Base):
    __tablename__ = "content_pieces"
    id = Column(Integer, primary_key=True)
    content_type = Column(Enum(ContentType))
    topic = Column(String(255))
    content = Column(Text)
    scheduled_at = Column(DateTime)
    published_at = Column(DateTime)
    status = Column(String(50), default="draft")  # draft, scheduled, published
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
