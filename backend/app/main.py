import os
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from backend.app.database import get_db, check_db_connection, init_db
from backend.app.models import (
    LearningProgress,
    StudyDocument,
    DocumentChunk,
    Quiz,
    QuizAttempt,
    StudyPlan,
    User,
    DSAActivity,
    StudyTask,
)
from backend.app.schemas import (
    LearningProgressCreate,
    LearningProgressResponse,
    AskQuestionRequest,
    AskQuestionResponse,
    DocumentResponse,
    RagAskRequest,
    RagAskResponse,
    QuizGenerateRequest,
    QuizResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizAttemptSummary,
    TargetedQuizRequest,
    ProgressAnalyticsResponse,
    LearnerProfileResponse,
    StudyPlanGenerateRequest,
    StudyPlanResponse,
    MilestoneStatusUpdateRequest,
    AgentRemediationRequest,
    AgentEvaluationRequest,
    AgentSystemStatusResponse,
    SignupRequest,
    LoginRequest,
    UserResponse,
    AuthResponse,
    DSALogRequest,
    DSAActivityResponse,
    DSAHeatmapResponse,
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    CalendarTasksResponse,
)
from backend.app.services.gemini_service import (
    is_gemini_configured,
    generate_learning_explanation,
    DEFAULT_MODEL,
    GeminiServiceUnavailableError,
    GeminiRateLimitError,
)
from backend.app.services.rag_service import (
    ingest_document,
    answer_from_notes,
    EMBEDDING_MODEL,
)
from backend.app.services.quiz_service import (
    generate_quiz,
    evaluate_quiz_submission,
    get_quiz_by_id,
    list_quizzes,
    list_quiz_attempts,
    generate_targeted_quiz,
    get_progress_analytics,
)
from backend.app.services.auth_service import (
    register_user,
    authenticate_user,
    get_user_by_id_or_username,
    decode_access_token,
)
from backend.app.services.dsa_service import (
    log_dsa_problem,
    get_dsa_heatmap_data,
    get_recent_dsa_problems,
    delete_dsa_problem,
)
from backend.app.services.calendar_service import (
    get_calendar_tasks,
    create_calendar_task,
    update_calendar_task,
    toggle_task_completion,
    delete_calendar_task,
)
from backend.app.agents import orchestrator

# Load environment variables
load_dotenv()
backend_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(backend_env_path):
    load_dotenv(backend_env_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup if database is configured
    is_connected, _ = check_db_connection()
    if is_connected:
        init_db()
    yield


app = FastAPI(
    title="CloudLearn AI Backend",
    description="Agentic personalized learning platform with Gemini & Study Notes RAG",
    version="0.4.0",
    lifespan=lifespan,
)

# Configure CORS: Allow all origins in production or comma-separated list from environment
origins_str = os.getenv("CORS_ORIGINS", "*")
origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in origins or not origins else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to CloudLearn AI API",
        "docs_url": "/docs",
        "health_check": "/health",
        "db_health": "/health/db",
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_connected, db_message = check_db_connection()
    doc_count = 0
    chunk_count = 0
    quiz_count = 0
    attempt_count = 0

    if db_connected:
        init_db()
        try:
            doc_count = db.query(StudyDocument).count()
            chunk_count = db.query(DocumentChunk).count()
            quiz_count = db.query(Quiz).count()
            attempt_count = db.query(QuizAttempt).count()
            db.commit()
        except Exception:
            pass

    gemini_ready = is_gemini_configured()

    return {
        "status": "ok",
        "project": "CloudLearn AI",
        "database": {
            "connected": db_connected,
            "message": db_message,
        },
        "gemini": {
            "configured": gemini_ready,
            "model": DEFAULT_MODEL,
            "message": "Gemini API ready" if gemini_ready else "GEMINI_API_KEY is not set in backend/.env",
        },
        "rag": {
            "ready": db_connected and gemini_ready,
            "embedding_model": EMBEDDING_MODEL,
            "documents_count": doc_count,
            "chunks_count": chunk_count,
        },
        "quizzes": {
            "total_quizzes": quiz_count,
            "total_attempts": attempt_count,
        },
        "agents": {
            "orchestrator": "operational",
            "active_agents": 5,
            "status": "ready",
        },
    }


@app.get("/health/db")
def health_db_check():
    is_connected, message = check_db_connection()
    if is_connected:
        init_db()
    return {
        "connected": is_connected,
        "message": message,
    }


# ==========================================
# GEMINI DIRECT Q&A
# ==========================================

@app.post("/api/ask", response_model=AskQuestionResponse)
def ask_question(req: AskQuestionRequest):
    """
    Answers a student question with clear, structured, beginner-friendly explanations
    powered by the official Google Gen AI SDK.
    """
    try:
        result = generate_learning_explanation(question=req.question, topic=req.topic)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ==========================================
# STUDY NOTES RAG PIPELINE
# ==========================================

@app.post("/api/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    user_id: str = Form("demo-user"),
    db: Session = Depends(get_db),
):
    """
    Uploads a study note (PDF, TXT, or MD), extracts text, splits into chunks,
    generates vector embeddings with Gemini, and stores them in Neon pgvector.
    """
    allowed_exts = [".pdf", ".txt", ".md"]
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(allowed_exts)}",
        )

    # Read content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {str(e)}")

    # Check file size (max 15MB)
    max_size = 15 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="File size exceeds the 15MB limit.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        doc = ingest_document(
            db=db,
            filename=file.filename or "uploaded_document",
            file_bytes=content,
            user_id=user_id,
            topic=topic,
            title=title,
        )
        return doc.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and index document: {str(e)}")


@app.get("/api/documents", response_model=List[DocumentResponse])
def list_documents(user_id: str = "demo-user", db: Session = Depends(get_db)):
    """Lists all uploaded study notes and documents for a user."""
    try:
        docs = (
            db.query(StudyDocument)
            .filter(StudyDocument.user_id == user_id)
            .order_by(StudyDocument.created_at.desc())
            .all()
        )
        db.commit()
        return [d.to_dict() for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {str(e)}")


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int, user_id: str = "demo-user", db: Session = Depends(get_db)):
    """Deletes a study document and cascades removal of all its vector chunks."""
    doc = (
        db.query(StudyDocument)
        .filter(StudyDocument.id == document_id, StudyDocument.user_id == user_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        db.delete(doc)
        db.commit()
        return {"status": "deleted", "document_id": document_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@app.post("/api/rag/ask", response_model=RagAskResponse)
def ask_from_notes(req: RagAskRequest, db: Session = Depends(get_db)):
    """
    Answers a student question grounded strictly in their uploaded study notes
    using Neon pgvector cosine similarity search and Gemini 3.8 Flash.
    """
    try:
        result = answer_from_notes(
            db=db,
            question=req.question,
            user_id=req.user_id,
            document_id=req.document_id,
            topic=req.topic,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG question answering failed: {str(e)}")


# ==========================================
# LEARNING PROGRESS TRACKING
# ==========================================

@app.get("/api/progress")
def list_progress(user_id: str = "demo-user", db: Session = Depends(get_db)):
    """Fetch learning progress records for a user."""
    try:
        records = (
            db.query(LearningProgress)
            .filter(LearningProgress.user_id == user_id)
            .order_by(LearningProgress.updated_at.desc())
            .all()
        )
        db.commit()
        return [r.to_dict() for r in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch progress: {str(e)}")


@app.post("/api/progress", response_model=LearningProgressResponse)
def create_progress(data: LearningProgressCreate, db: Session = Depends(get_db)):
    """Create a new learning progress record (tracks topic mastery and mistakes)."""
    try:
        record = LearningProgress(
            user_id=data.user_id,
            topic=data.topic,
            subtopic=data.subtopic,
            total_questions=data.total_questions,
            correct_answers=data.correct_answers,
            mistake_count=data.mistake_count,
            mastery_score=data.mastery_score,
            last_mistake_summary=data.last_mistake_summary,
            status=data.status,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save progress: {str(e)}")


# ==========================================
# AI QUIZ GENERATION & ATTEMPTS
# ==========================================

@app.post("/api/quizzes/generate", response_model=QuizResponse)
def api_generate_quiz(req: QuizGenerateRequest, db: Session = Depends(get_db)):
    """
    Generates high-yield multiple-choice questions (4 options, 1 correct)
    from uploaded study notes or topic using Gemini, and saves to Neon PostgreSQL.
    """
    try:
        quiz = generate_quiz(
            db=db,
            topic=req.topic,
            document_id=req.document_id,
            num_questions=req.num_questions,
            difficulty=req.difficulty,
            user_id=req.user_id,
        )
        return quiz.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")


@app.get("/api/quizzes/{quiz_id}", response_model=QuizResponse)
def api_get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    """Retrieves a specific quiz with questions."""
    quiz = get_quiz_by_id(db=db, quiz_id=quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz.to_dict()


@app.post("/api/quizzes/submit", response_model=QuizSubmitResponse)
def api_submit_quiz(req: QuizSubmitRequest, db: Session = Depends(get_db)):
    """
    Submits student answers for a quiz.
    Evaluates score, returns correct answers & explanations, saves attempt to Neon,
    and updates learning progress.
    """
    try:
        result = evaluate_quiz_submission(
            db=db,
            quiz_id=req.quiz_id,
            user_id=req.user_id,
            answers=req.answers,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz evaluation failed: {str(e)}")


@app.get("/api/quizzes")
def api_list_quizzes(user_id: str = "demo-user", limit: int = 20, db: Session = Depends(get_db)):
    """Lists recent quizzes for the user."""
    try:
        quizzes = list_quizzes(db=db, user_id=user_id, limit=limit)
        return [q.to_dict() for q in quizzes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quizzes: {str(e)}")


@app.get("/api/quizzes/attempts/history")
def api_list_attempts(user_id: str = "demo-user", limit: int = 20, db: Session = Depends(get_db)):
    """Lists recent quiz attempts and scores for the user."""
    try:
        attempts = list_quiz_attempts(db=db, user_id=user_id, limit=limit)
        res = []
        for a in attempts:
            item = a.to_dict()
            item["quiz_title"] = a.quiz.title if a.quiz else "Quiz"
            item["quiz_topic"] = a.quiz.topic if a.quiz else "General"
            res.append(item)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quiz attempts: {str(e)}")


@app.get("/api/progress/analytics", response_model=ProgressAnalyticsResponse)
def api_progress_analytics(user_id: str = "demo-user", db: Session = Depends(get_db)):
    """
    Returns aggregated mastery analytics, weak concepts, topic progress,
    adaptive recommendations, and quiz history.
    """
    try:
        data = get_progress_analytics(db=db, user_id=user_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch progress analytics: {str(e)}")


@app.post("/api/quizzes/generate-targeted", response_model=QuizResponse)
def api_generate_targeted_quiz(req: TargetedQuizRequest, db: Session = Depends(get_db)):
    """
    Generates a targeted MCQ quiz focused on remediating specific student misconceptions
    using Gemini and relevant uploaded study notes via RAG.
    """
    try:
        quiz = generate_targeted_quiz(
            db=db,
            topic=req.topic,
            focus_concepts=req.focus_concepts,
            num_questions=req.num_questions,
            user_id=req.user_id,
        )
        return quiz.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate targeted quiz: {str(e)}")


# ========================================================
# MULTI-AGENT LEARNING SYSTEM ENDPOINTS
# ========================================================

@app.get("/api/agents/status", response_model=AgentSystemStatusResponse)
def api_agents_status(user_id: str = "demo-user", db: Session = Depends(get_db)):
    """
    Returns operational status, live telemetry, and active study plan
    for the 5 specialized AI learning agents coordinated by the central orchestrator.
    """
    try:
        return orchestrator.get_agent_system_status(user_id=user_id, db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents status: {str(e)}")


@app.get("/api/agents/profile", response_model=LearnerProfileResponse)
def api_learner_profile(user_id: str = "demo-user", db: Session = Depends(get_db)):
    """
    Queries the Learner Profiling Agent to analyze quiz history, identify
    weak concepts, determine mastery tier, and calculate learning velocity.
    """
    try:
        profile = orchestrator.profiler.analyze_profile(user_id=user_id, db=db)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate learner profile: {str(e)}")


@app.post("/api/agents/study-plan", response_model=StudyPlanResponse)
def api_generate_study_plan(req: StudyPlanGenerateRequest, db: Session = Depends(get_db)):
    """
    Coordinates Learner Profiling Agent, Content Recommendation Agent,
    and Curriculum Planner Agent to create and persist an adaptive multi-phase study plan.
    """
    try:
        plan = orchestrator.generate_study_plan(
            user_id=req.user_id,
            goal=req.goal,
            target_timeline=req.target_timeline,
            focus_topics=req.focus_topics,
            db=db,
        )
        return plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate study plan: {str(e)}")


@app.get("/api/agents/study-plan", response_model=Optional[StudyPlanResponse])
def api_get_study_plan(user_id: str = "demo-user", db: Session = Depends(get_db)):
    """
    Retrieves the learner's active personalized study plan from Neon PostgreSQL.
    """
    try:
        plan = orchestrator.get_active_study_plan(user_id=user_id, db=db)
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch active study plan: {str(e)}")


@app.patch("/api/agents/study-plan/milestone", response_model=StudyPlanResponse)
def api_update_milestone(req: MilestoneStatusUpdateRequest, db: Session = Depends(get_db)):
    """
    Updates the status of a specific milestone in the user's active study plan.
    """
    try:
        updated_plan = orchestrator.update_milestone_status(
            user_id=req.user_id,
            milestone_id=req.milestone_id,
            new_status=req.new_status,
            db=db,
        )
        return updated_plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update milestone: {str(e)}")


@app.post("/api/agents/remediate")
def api_agent_remediate(req: AgentRemediationRequest, db: Session = Depends(get_db)):
    """
    Coordinates Profiler, Recommender, and Quiz Agent to generate a targeted
    remediation quiz grounded via RAG in uploaded notes.
    """
    try:
        result = orchestrator.orchestrate_targeted_remediation(
            user_id=req.user_id,
            topic=req.topic,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to orchestrate remediation: {str(e)}")


@app.post("/api/agents/evaluate")
def api_agent_evaluate(req: AgentEvaluationRequest, db: Session = Depends(get_db)):
    """
    Coordinates Evaluation Agent to grade quiz submissions, analyze knowledge gaps,
    update LearningProgress in Neon, and auto-update milestone completion in the study plan.
    """
    try:
        result = orchestrator.orchestrate_quiz_evaluation(
            user_id=req.user_id,
            quiz_id=req.quiz_id,
            answers=req.answers,
            milestone_id=req.milestone_id,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to orchestrate quiz evaluation: {str(e)}")


# ========================================================
# AUTHENTICATION ENDPOINTS (LOGIN, SIGNUP, ME, LOGOUT)
# ========================================================

@app.post("/api/auth/signup", response_model=AuthResponse)
def api_signup(req: SignupRequest, db: Session = Depends(get_db)):
    """
    Registers a new user account with secure PBKDF2 password hashing.
    Returns user profile and authentication token.
    """
    try:
        user, token = register_user(
            db=db,
            username=req.username,
            email=req.email,
            password=req.password,
            full_name=req.full_name,
        )
        return {
            "user": user.to_dict(),
            "token": token,
            "access_token": token,
            "message": f"Welcome to CloudLearn AI, {user.full_name}!",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/api/auth/login", response_model=AuthResponse)
def api_login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates user with username or email and password.
    Returns user profile and secure JWT access token.
    """
    identifier = req.username_or_email or req.username
    if not identifier:
        raise HTTPException(status_code=400, detail="Username or email is required.")

    result = authenticate_user(
        db=db,
        username_or_email=identifier,
        password=req.password,
    )
    if not result:
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    user, token = result
    return {
        "user": user.to_dict(),
        "token": token,
        "access_token": token,
        "message": f"Welcome back, {user.full_name}!",
    }


@app.get("/api/auth/me", response_model=UserResponse)
def api_get_me(
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns current authenticated user identity from Bearer token or user_id.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user = get_user_by_id_or_username(db, payload["sub"])
            if user:
                return user.to_dict()

    if user_id:
        user = get_user_by_id_or_username(db, user_id)
        if user:
            return user.to_dict()

    return {
        "id": 0,
        "user_id": user_id or "demo-user",
        "username": user_id or "demo-user",
        "email": f"{user_id or 'demo-user'}@cloudlearn.ai",
        "full_name": "Demo Learner" if (user_id == "demo-user" or not user_id) else user_id,
        "is_active": True,
    }


@app.post("/api/auth/logout")
def api_logout():
    """Logs out user session."""
    return {"message": "Logged out successfully."}


# ========================================================
# DSA HEATMAP & PROBLEM LOG ENDPOINTS
# ========================================================

@app.get("/api/dsa/heatmap", response_model=DSAHeatmapResponse)
def api_get_dsa_heatmap(
    user_id: str = "demo-user",
    days: int = 365,
    db: Session = Depends(get_db),
):
    """
    Returns LeetCode/GitHub-style green activity grid, streaks, topic breakdown,
    and difficulty statistics from Neon PostgreSQL.
    """
    try:
        return get_dsa_heatmap_data(db=db, user_id=user_id, days_span=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch DSA heatmap: {str(e)}")


@app.post("/api/dsa/log", response_model=DSAActivityResponse)
def api_log_dsa_problem(req: DSALogRequest, db: Session = Depends(get_db)):
    """
    Logs a solved DSA problem into Neon PostgreSQL.
    """
    try:
        activity = log_dsa_problem(
            db=db,
            user_id=req.user_id,
            problem_title=req.problem_title,
            platform=req.platform,
            difficulty=req.difficulty,
            topic=req.topic,
            activity_date=req.activity_date,
            problem_url=req.problem_url,
            notes=req.notes,
        )
        return activity.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log DSA problem: {str(e)}")


@app.get("/api/dsa/problems")
def api_get_dsa_problems(
    user_id: str = "demo-user",
    limit: int = 30,
    db: Session = Depends(get_db),
):
    """Returns recent solved problems for the user."""
    try:
        return get_recent_dsa_problems(db=db, user_id=user_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch DSA problems: {str(e)}")


@app.delete("/api/dsa/problems/{problem_id}")
def api_delete_dsa_problem(
    problem_id: int,
    user_id: str = "demo-user",
    db: Session = Depends(get_db),
):
    """Deletes a logged DSA problem."""
    success = delete_dsa_problem(db=db, user_id=user_id, activity_id=problem_id)
    if not success:
        raise HTTPException(status_code=404, detail="Problem log not found or unauthorized.")
    return {"message": "Problem record deleted successfully."}


# ========================================================
# STUDY CALENDAR ENDPOINTS
# ========================================================

@app.get("/api/calendar/tasks", response_model=CalendarTasksResponse)
def api_get_calendar_tasks(
    user_id: str = "demo-user",
    month: Optional[str] = None,
    category: Optional[str] = None,
    is_completed: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieves monthly/weekly calendar tasks with completion rate summary.
    """
    try:
        return get_calendar_tasks(
            db=db,
            user_id=user_id,
            month=month,
            category=category,
            is_completed=is_completed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendar tasks: {str(e)}")


@app.post("/api/calendar/tasks", response_model=TaskResponse)
def api_create_calendar_task(req: TaskCreateRequest, db: Session = Depends(get_db)):
    """
    Schedules a new study calendar task in Neon PostgreSQL.
    """
    try:
        task = create_calendar_task(
            db=db,
            user_id=req.user_id,
            title=req.title,
            task_date=req.task_date,
            category=req.category,
            description=req.description,
            start_time=req.start_time,
            end_time=req.end_time,
            priority=req.priority,
        )
        return task.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create calendar task: {str(e)}")


@app.put("/api/calendar/tasks/{task_id}", response_model=TaskResponse)
def api_update_calendar_task(
    task_id: int,
    req: TaskUpdateRequest,
    user_id: str = "demo-user",
    db: Session = Depends(get_db),
):
    """
    Updates a scheduled study task.
    """
    task = update_calendar_task(
        db=db,
        user_id=user_id,
        task_id=task_id,
        title=req.title,
        description=req.description,
        category=req.category,
        task_date=req.task_date,
        start_time=req.start_time,
        end_time=req.end_time,
        priority=req.priority,
        is_completed=req.is_completed,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task.to_dict()


@app.patch("/api/calendar/tasks/{task_id}/toggle", response_model=TaskResponse)
def api_toggle_calendar_task(
    task_id: int,
    user_id: str = "demo-user",
    db: Session = Depends(get_db),
):
    """
    Toggles completion status for a study task.
    """
    task = toggle_task_completion(db=db, user_id=user_id, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task.to_dict()


@app.delete("/api/calendar/tasks/{task_id}")
def api_delete_calendar_task(
    task_id: int,
    user_id: str = "demo-user",
    db: Session = Depends(get_db),
):
    """
    Deletes a scheduled study task.
    """
    success = delete_calendar_task(db=db, user_id=user_id, task_id=task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"message": "Task deleted successfully."}


