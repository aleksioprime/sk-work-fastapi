from datetime import datetime
import uuid

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func, text


from src.db.postgres import Base


class Promo(Base):
    __tablename__ = "promos"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    mode = Column(String(10), nullable=False)
    promo_common = Column(String(50), nullable=True)
    promo_unique = Column(JSONB, nullable=True)
    description = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    target = Column(JSONB, nullable=True)
    max_count = Column(Integer, nullable=False)
    active_from = Column(DateTime, nullable=True)
    active_until = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Связи с другими таблицами
    company = relationship("Company", back_populates="promos")
    comments = relationship("Comment", back_populates="promo")
    likes = relationship("Like", back_populates="promo")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promos.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    promo = relationship("Promo", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Like(Base):
    __tablename__ = "likes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promos.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    promo = relationship("Promo", back_populates="likes")
    user = relationship("User", back_populates="likes")


class PromoActivation(Base):
    __tablename__ = "promo_activations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promos.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activation_value = Column(String(50), nullable=True)
    activated_at = Column(DateTime, server_default=func.now())

    promo = relationship("Promo")
    user = relationship("User")
