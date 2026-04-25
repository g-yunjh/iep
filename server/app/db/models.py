from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    current_level = Column(String, nullable=True)
    disability_type = Column(String, nullable=True)
    additional_diagnoses = Column(String, nullable=True)
    behavioral_traits = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    feedbacks = relationship("Feedback", back_populates="student")

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    performance = Column(String)
    scaffolding_effectiveness = Column(Text)
    disability_type = Column(String, nullable=True)
    teacher_description = Column(Text, nullable=True)
    llm_analysis = Column(JSON, nullable=True)
    scaffolding_recommendations = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="feedbacks")
