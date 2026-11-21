from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from backend.app.database import Base

EMBEDDING_DIM = 768


def utc_now():
    return datetime.now(timezone.utc)


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), index=True, nullable=False, default="demo-user")
    topic = Column(String(200), index=True, nullable=False)
    subtopic = Column(String(200), nullable=True)
    total_questions = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    mistake_count = Column(Integer, default=0, nullable=False)
    mastery_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 100.0
    last_mistake_summary = Column(Text, nullable=True)
    status = Column(String(50), default="in_progress", nullable=False)  # needs_review, in_progress, mastered
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "mistake_count": self.mistake_count,
            "mastery_score": self.mastery_score,
            "last_mistake_summary": self.last_mistake_summary,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StudyDocument(Base):
    __tablename__ = "study_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), index=True, nullable=False, default="demo-user")
    filename = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    topic = Column(String(200), nullable=True)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    page_count = Column(Integer, default=1, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "title": self.title,
            "topic": self.topic,
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("study_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("StudyDocument", back_populates="chunks")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), index=True, nullable=False, default="demo-user")
    title = Column(String(255), nullable=False)
    topic = Column(String(200), index=True, nullable=False)
    document_id = Column(Integer, ForeignKey("study_documents.id", ondelete="SET NULL"), nullable=True)
    difficulty = Column(String(50), default="intermediate", nullable=False)
    total_questions = Column(Integer, default=5, nullable=False)
    questions_data = Column(Text, nullable=False)  # JSON-encoded array of questions
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")
    document = relationship("StudyDocument")

    def to_dict(self):
        import json
        try:
            questions = json.loads(self.questions_data)
        except Exception:
            questions = []

        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "topic": self.topic,
            "document_id": self.document_id,
            "document_title": self.document.title if self.document else None,
            "difficulty": self.difficulty,
            "total_questions": self.total_questions,
            "questions": questions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(100), index=True, nullable=False, default="demo-user")
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    answers_data = Column(Text, nullable=False)  # JSON-encoded evaluation of each question
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    quiz = relationship("Quiz", back_populates="attempts")

    def to_dict(self):
        import json
        try:
            answers = json.loads(self.answers_data)
        except Exception:
            answers = []

        return {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "quiz_title": self.quiz.title if self.quiz else "Quiz",
            "quiz_topic": self.quiz.topic if self.quiz else "General",
            "user_id": self.user_id,
            "score": self.score,
            "total_questions": self.total_questions,
            "percentage": self.percentage,
            "answers": answers,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), index=True, nullable=False, default="demo-user")
    goal = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    target_timeline = Column(String(100), default="2 Weeks", nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, completed, archived
    plan_data = Column(Text, nullable=False)  # JSON-encoded dict of phases, milestones, recommendations, agent trace
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self):
        import json
        try:
            parsed = json.loads(self.plan_data)
        except Exception:
            parsed = {}

        return {
            "id": self.id,
            "user_id": self.user_id,
            "goal": self.goal,
            "title": self.title,
            "target_timeline": self.target_timeline,
            "status": self.status,
            "phases": parsed.get("phases", []),
            "content_recommendations": parsed.get("content_recommendations", []),
            "agent_trace": parsed.get("agent_trace", {}),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.username,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name or self.username,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DSAActivity(Base):
    __tablename__ = "dsa_activities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), index=True, nullable=False, default="demo-user")
    problem_title = Column(String(255), nullable=False)
    problem_url = Column(String(500), nullable=True)
    platform = Column(String(100), default="LeetCode", nullable=False)  # LeetCode, Codeforces, HackerRank, GeeksforGeeks, CloudLearn
    difficulty = Column(String(50), default="Medium", nullable=False)   # Easy, Medium, Hard
    topic = Column(String(100), default="Arrays", nullable=False)       # Arrays, DP, Graphs, Trees, Strings, etc.
    notes = Column(Text, nullable=True)
    activity_date = Column(String(10), index=True, nullable=False)      # "YYYY-MM-DD"
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "problem_title": self.problem_title,
            "problem_url": self.problem_url,
            "platform": self.platform,
            "difficulty": self.difficulty,
            "topic": self.topic,
            "notes": self.notes,
            "activity_date": self.activity_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), index=True, nullable=False, default="demo-user")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="General", nullable=False)   # OS, DSA, DBMS, AI/ML, Revision, Exam Prep, Placement, General
    task_date = Column(String(10), index=True, nullable=False)          # "YYYY-MM-DD"
    start_time = Column(String(10), nullable=True)                      # "14:00"
    end_time = Column(String(10), nullable=True)                        # "15:30"
    priority = Column(String(20), default="medium", nullable=False)     # low, medium, high
    is_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "task_date": self.task_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "priority": self.priority,
            "is_completed": self.is_completed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

