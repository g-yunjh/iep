from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    disability_type = Column(String, nullable=True)     # 주 장애 유형
    additional_diagnoses = Column(String, nullable=True) # 중복 장애 (ADHD 등)
    behavioral_traits = Column(Text, nullable=True)     # 행동적 특성 (화내는 트리거 등)
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
    disability_type = Column(String, nullable=True)  # 장애 유형 (지적장애, 학습장애, 자폐성장애 등)
    teacher_description = Column(Text, nullable=True)  # 선생님/부모님의 아동 상태 설명
    llm_analysis = Column(JSON, nullable=True)  # LLM 분석 결과 (JSON)
    scaffolding_recommendations = Column(JSON, nullable=True)  # 스캐폴딩 추천사항 (JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="feedbacks")