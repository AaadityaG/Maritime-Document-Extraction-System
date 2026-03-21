from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    extractions = relationship("Extraction", back_populates="session", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="session", cascade="all, delete-orphan")
    validations = relationship("Validation", back_populates="session", cascade="all, delete-orphan")


class Extraction(Base):
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


class Job(Base):
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


class Validation(Base):
    __tablename__ = "validations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="validations")


# Database setup functions
class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.async_session_maker = None
    
    async def connect(self):
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            future=True
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def disconnect(self):
        if self.engine:
            await self.engine.dispose()
    
    def get_session(self) -> AsyncSession:
        return self.async_session_maker()
