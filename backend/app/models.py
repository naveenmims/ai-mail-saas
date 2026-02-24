from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base




class Organization(Base):
    from sqlalchemy import Column, Integer, Text, Date, DateTime
    from sqlalchemy.sql import func
    # (keep your existing imports; only add what’s missing)
    
    plan_code = Column(Text, default="free")
    credits_balance = Column(Integer, nullable=False, default=0)
    credits_monthly = Column(Integer, nullable=False, default=0)
    billing_cycle_anchor = Column(Date, nullable=True)
    credits_reset_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_credit_reset_at = Column(DateTime(timezone=True), nullable=True)

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    website_url = Column(Text, nullable=True, default="")

    # Stripe / billing
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=False, default="inactive")

    # Tenant settings
    support_name = Column(Text, nullable=True)
    support_email = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    kb_text = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)

    # Controls
    auto_reply = Column(Integer, default=1)
    max_replies_per_hour = Column(Integer, default=10)

    # Enterprise toggle + cooldown
    cooldown_hours = Column(Integer, default=24, nullable=False)
    auto_reply_enabled = Column(Boolean, default=True, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="owner")

    organization = relationship("Organization")


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True, nullable=False)

    # identity
    label: Mapped[str] = mapped_column(String(100), nullable=False, default="Primary")
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # IMAP settings (for receiving)
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, default=993)
    imap_username: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_password: Mapped[str] = mapped_column(String(255), nullable=False)  # encrypt later

    # SendGrid (for sending)
    sendgrid_api_key: Mapped[str] = mapped_column(String(255), nullable=False)  # encrypt later
    from_name: Mapped[str] = mapped_column(String(255), nullable=False, default="AI Mail SaaS")


class ConversationAudit(Base):
    __tablename__ = "conversation_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    org_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    thread_key: Mapped[str] = mapped_column(String(512), index=True, nullable=False)

    customer_email: Mapped[Optional[str]] = mapped_column(String(320), index=True, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(998), nullable=True)

    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # "IN" / "OUT"

    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    email_message_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    in_reply_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    references_header: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_tokens_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_tokens_out: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkerStatus(Base):
    __tablename__ = "worker_status"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    worker_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_email_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    last_email_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_thread_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    lock_health_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    credits_health_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy import Date  # add if not present

class OrgCredits(Base):
    __tablename__ = "org_credits"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    plan = Column(String(50), nullable=True)                # e.g., free/pro
    credits_total = Column(Integer, nullable=False, default=0)
    credits_used = Column(Integer, nullable=False, default=0)
    credits_reset_at = Column(Date, nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OrgUsage(Base):
    __tablename__ = "org_usage"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    event = Column(String(100), nullable=False, index=True)
    qty = Column(Integer, nullable=False, default=1)
    meta = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.sql import func

class ReplyThreadLock(Base):
    __tablename__ = "reply_thread_locks"

    id = Column(Integer, primary_key=True)

    org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    thread_key = Column(Text, nullable=False)

    # SQLite has this column and it is NOT NULL there
    bucket_start = Column(DateTime(timezone=True), nullable=False)

    # SQLite has this column (VARCHAR(64))
    worker_id = Column(String(64), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("org_id", "thread_key", name="uq_reply_thread_locks_org_thread"),
    )

