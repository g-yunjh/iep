from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    center_id = Column(Integer, ForeignKey("centers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    center = relationship("Center", back_populates="students")
    feedbacks = relationship("Feedback", back_populates="student")

class Center(Base):
    __tablename__ = "centers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    strategies = Column(JSON, default=list)  # 효과가 좋았던 전략들 리스트
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    students = relationship("Student", back_populates="center")

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    performance = Column(String)  # 학습 수행도
    scaffolding_effectiveness = Column(Text)  # 스캐폴딩 효과성 피드백
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="feedbacks")