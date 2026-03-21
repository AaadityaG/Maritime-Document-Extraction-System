"""Database models for SMDE"""

from app.core.database import Base
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid


class Session(Base):
    """Upload session model"""
    
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    extractions = relationship("Extraction", back_populates="session", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="session", cascade="all, delete-orphan")
    validations = relationship("Validation", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session(id={self.id})>"


class Extraction(Base):
    """Extracted document data model"""
    
    __tablename__ = "extractions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    document_type = Column(String)
    applicable_role = Column(String)
    confidence = Column(String)
    holder_name = Column(String)
    date_of_birth = Column(String)
    sirb_number = Column(String)
    passport_number = Column(String)
    fields_json = Column(Text)
    validity_json = Column(Text)
    medical_data_json = Column(Text)
    flags_json = Column(Text)
    is_expired = Column(Boolean, default=False)
    summary = Column(Text)
    raw_llm_response = Column(Text)
    processing_time_ms = Column(Integer)
    status = Column(String, default="COMPLETE")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    session = relationship("Session", back_populates="extractions")
    
    def __repr__(self):
        return f"<Extraction(id={self.id}, file_name={self.file_name})>"


class Job(Base):
    """Async job queue model"""
    
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"))
    extraction_id = Column(String, ForeignKey("extractions.id"), nullable=True)
    status = Column(String, default="QUEUED")
    error_code = Column(String)
    error_message = Column(Text)
    queued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    session = relationship("Session", back_populates="jobs")
    extraction = relationship("Extraction", backref="jobs")
    
    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status})>"


class Validation(Base):
    """Cross-document validation result model"""
    
    __tablename__ = "validations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="validations")
    
    def __repr__(self):
        return f"<Validation(id={self.id}, session_id={self.session_id})>"
