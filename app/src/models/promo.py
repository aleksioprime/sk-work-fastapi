from datetime import datetime
import uuid

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB


from src.db.postgres import Base


class Promo(Base):
    __tablename__ = "promos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    mode = Column(String(10), nullable=False)
    promo_common = Column(String(50), nullable=True)
    promo_unique = Column(JSON, nullable=True)
    description = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    target = Column(JSONB, nullable=True)
    max_count = Column(Integer, nullable=False)
    active_from = Column(DateTime, nullable=False)
    active_until = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи с другими таблицами
    company = relationship("Company", back_populates="promos")
    comments = relationship("Comment", back_populates="promo")
    likes = relationship("Like", back_populates="promo")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promos.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    promo = relationship("Promo", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Like(Base):
    __tablename__ = "likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promos.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    promo = relationship("Promo", back_populates="likes")
    user = relationship("User", back_populates="likes")


class PromoActivation(Base):
    __tablename__ = "promo_activations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promos.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    activation_value = Column(String(50), nullable=True)
    activated_at = Column(DateTime, default=datetime.utcnow)

    promo = relationship("Promo")
    user = relationship("User")
