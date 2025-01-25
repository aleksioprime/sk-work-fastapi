from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import uuid

from src.db.postgres import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), unique=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __init__(self, password: str, name: str, email: str,) -> None:
        self.name = name
        self.email = email
        self.password = self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    promos = relationship("Promo", back_populates="company")