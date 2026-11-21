from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LearningProgressCreate(BaseModel):
    user_id: str = Field(default="demo-user", description="Identifier of the learner")
    topic: str = Field(..., description="Subject or domain, e.g. Data Structures")
    subtopic: Optional[str] = Field(None, description="Granular concept, e.g. Binary Search Trees")
    total_questions: int = Field(default=0, ge=0)
    correct_answers: int = Field(default=0, ge=0)
    mistake_count: int = Field(default=0, ge=0)
    mastery_score: float = Field(default=0.0, ge=0.0, le=100.0)
    last_mistake_summary: Optional[str] = Field(None, description="Summary of student misconception")
    status: str = Field(default="in_progress", description="needs_review | in_progress | mastered")


class LearningProgressResponse(LearningProgressCreate):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class AskQuestionRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The student's question or topic they want explained",
        examples=["What is the difference between paging and segmentation in OS?"],
    )
    topic: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional subject area, e.g. Operating Systems, Data Structures",
        examples=["Operating Systems"],
    )


class AskQuestionResponse(BaseModel):
    question: str
    topic: Optional[str] = None
    answer: str
    model: str


class DocumentResponse(BaseModel):
    id: int
    user_id: str
    filename: str
    title: str
    topic: Optional[str] = None
    file_size_bytes: int
    page_count: int
    chunk_count: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class RagSource(BaseModel):
    document_id: int
    document_title: str
    page_number: Optional[int] = None
    excerpt: str
    similarity_score: float


class RagAskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Question to ask grounded in uploaded notes",
    )
    user_id: str = Field(default="demo-user", description="User ID")
    document_id: Optional[int] = Field(None, description="Optional specific document to query")
    topic: Optional[str] = Field(None, description="Optional subject topic")


class RagAskResponse(BaseModel):
    question: str
    topic: Optional[str] = None
    answer: str
    model: str
    has_context: bool
    sources: List[RagSource] = []


# ==========================================
# QUIZ SCHEMAS
# ==========================================

class QuizQuestion(BaseModel):
    id: int
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4, description="Exactly 4 options")
    correct_index: Optional[int] = Field(None, ge=0, le=3)
    explanation: Optional[str] = None
    source_reference: Optional[str] = None


class QuizGenerateRequest(BaseModel):
    topic: Optional[str] = Field(None, description="Domain or topic, e.g. Operating Systems")
    document_id: Optional[int] = Field(None, description="Optional study note document ID to ground the quiz")
    num_questions: int = Field(default=5, ge=1, le=10, description="Number of MCQs to generate (1 to 10)")
    difficulty: str = Field(default="intermediate", description="beginner | intermediate | advanced")
    user_id: str = Field(default="demo-user", description="User identifier")


class QuizResponse(BaseModel):
    id: int
    user_id: str
    title: str
    topic: str
    document_id: Optional[int] = None
    document_title: Optional[str] = None
    difficulty: str
    total_questions: int
    questions: List[QuizQuestion]
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class QuizSubmitRequest(BaseModel):
    quiz_id: int
    user_id: str = Field(default="demo-user")
    answers: dict = Field(..., description="Map of question id -> selected option index (0 to 3)")


class QuizQuestionEvaluation(BaseModel):
    question_id: int
    question: str
    options: List[str]
    selected_index: Optional[int] = None
    correct_index: int
    is_correct: bool
    explanation: str
    source_reference: Optional[str] = None


class QuizSubmitResponse(BaseModel):
    attempt_id: int
    quiz_id: int
    user_id: str
    score: int
    total_questions: int
    percentage: float
    results: List[QuizQuestionEvaluation]
    feedback: str
    mastery_status: str  # needs_review, in_progress, mastered
    created_at: Optional[str] = None


class QuizAttemptSummary(BaseModel):
    id: int
    quiz_id: int
    quiz_title: Optional[str] = None
    quiz_topic: Optional[str] = None
    user_id: str
    score: int
    total_questions: int
    percentage: float
    created_at: Optional[str] = None


class TargetedQuizRequest(BaseModel):
    topic: str = Field(..., description="Subject or weak topic to remediate, e.g. Operating Systems")
    focus_concepts: Optional[List[str]] = Field(None, description="Specific concepts or misconceptions to target")
    num_questions: int = Field(default=3, ge=1, le=10, description="Number of targeted questions")
    user_id: str = Field(default="demo-user", description="User identifier")


class TopicMasteryItem(BaseModel):
    topic: str
    subtopic: Optional[str] = None
    total_questions: int
    correct_answers: int
    mistake_count: int
    mastery_score: float
    status: str  # needs_review, in_progress, mastered
    trend: str  # improving, stable, declining
    attempts_count: int
    last_mistake_summary: Optional[str] = None
    updated_at: Optional[str] = None


class WeakTopicItem(BaseModel):
    topic: str
    mastery_score: float
    mistake_count: int
    missed_concepts: List[str]
    recommended_action: str


class StudyRecommendation(BaseModel):
    type: str  # remediate, explore, challenge
    topic: str
    title: str
    reason: str
    action: str  # generate_targeted, start_quiz, review_notes
    document_id: Optional[int] = None


class ProgressAnalyticsResponse(BaseModel):
    summary: dict
    topic_mastery: List[TopicMasteryItem]
    weak_topics: List[WeakTopicItem]
    next_recommendations: List[StudyRecommendation]
    attempts_timeline: List[dict]


# ========================================================
# MULTI-AGENT LEARNING SYSTEM SCHEMAS
# ========================================================

class LearnerProfileResponse(BaseModel):
    user_id: str
    overall_accuracy: float
    total_quizzes_taken: int
    total_questions_answered: int
    total_correct_answers: int
    mastered_topics: List[dict]
    in_progress_topics: List[dict]
    weak_topics: List[dict]
    learning_tier: str  # Foundational Beginner, Developing, Competent, Advanced Mastery
    learning_velocity: str  # Accelerating, Steady, Needs Reinforcement
    summary_narrative: str


class StudyPlanMilestone(BaseModel):
    id: str
    phase: str
    title: str
    topic: str
    action_type: str  # review_notes, targeted_quiz, concept_deep_dive, comprehensive_test
    description: str
    recommended_doc_title: Optional[str] = None
    recommended_doc_id: Optional[int] = None
    estimated_minutes: int = 30
    status: str = "pending"  # pending, in_progress, completed


class StudyPlanPhase(BaseModel):
    phase_name: str
    focus: str
    milestones: List[StudyPlanMilestone]


class StudyPlanGenerateRequest(BaseModel):
    user_id: str = Field(default="demo-user", description="User identifier")
    goal: str = Field(
        default="Master Core Computer Science & Technical Placements",
        description="Learner's target objective or curriculum focus"
    )
    target_timeline: str = Field(
        default="2 Weeks",
        description="Target duration (e.g. 1 Week, 2 Weeks, 1 Month)"
    )
    focus_topics: Optional[List[str]] = Field(
        default=None,
        description="Specific topics to prioritize in the curriculum"
    )


class StudyPlanResponse(BaseModel):
    id: Optional[int] = None
    user_id: str
    goal: str
    title: str
    target_timeline: str
    status: str
    phases: List[dict]
    content_recommendations: List[dict]
    agent_trace: dict
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MilestoneStatusUpdateRequest(BaseModel):
    user_id: str = Field(default="demo-user")
    milestone_id: str
    new_status: str = Field(..., description="Status: pending, in_progress, completed")


class AgentRemediationRequest(BaseModel):
    user_id: str = Field(default="demo-user")
    topic: Optional[str] = None


class AgentEvaluationRequest(BaseModel):
    quiz_id: int
    user_id: str = Field(default="demo-user")
    answers: dict = Field(..., description="Map of question id -> selected option index")
    milestone_id: Optional[str] = None


class AgentSystemStatusResponse(BaseModel):
    orchestrator_status: str
    agents: dict
    active_plan: Optional[dict] = None
    learner_profile_summary: dict


# ==========================================
# AUTH SCHEMAS
# ==========================================

class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., min_length=5, max_length=150, description="Valid email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password (at least 6 characters)")
    full_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    username_or_email: Optional[str] = Field(None, description="Username or email address")
    username: Optional[str] = Field(None, description="Alternative username field")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    id: int
    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    access_token: Optional[str] = None
    message: str = "Authenticated successfully"


# ==========================================
# DSA HEATMAP & PROBLEM LOG SCHEMAS
# ==========================================

class DSALogRequest(BaseModel):
    problem_title: str = Field(..., min_length=1, max_length=255, description="Title of the solved problem")
    platform: str = Field(default="LeetCode", description="Platform, e.g. LeetCode, Codeforces, HackerRank, GeeksforGeeks, CloudLearn")
    difficulty: str = Field(default="Medium", description="Easy, Medium, Hard")
    topic: str = Field(default="Arrays", description="Topic, e.g. Arrays, Strings, DP, Graphs, Trees, etc.")
    activity_date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format (defaults to today)")
    problem_url: Optional[str] = Field(None, max_length=500, description="Optional link to problem")
    notes: Optional[str] = Field(None, description="Optional brief notes or approach taken")
    user_id: str = Field(default="demo-user", description="User ID")


class DSAActivityResponse(BaseModel):
    id: int
    user_id: str
    problem_title: str
    problem_url: Optional[str] = None
    platform: str
    difficulty: str
    topic: str
    notes: Optional[str] = None
    activity_date: str
    created_at: Optional[str] = None


class DSAHeatmapDay(BaseModel):
    date: str
    count: int = 0
    problem_count: Optional[int] = 0
    level: int = 0  # 0 to 4
    intensity: Optional[int] = 0
    day_of_week: int = 0  # 0 (Mon) to 6 (Sun) or similar


class DSAHeatmapResponse(BaseModel):
    user_id: str
    total_problems: int
    current_streak: int
    max_streak: int
    active_days_count: int
    difficulty_breakdown: Dict[str, int]
    platform_breakdown: Dict[str, int]
    topic_breakdown: Dict[str, int]
    heatmap_days: List[DSAHeatmapDay]
    days: Optional[List[DSAHeatmapDay]] = None
    recent_problems: List[DSAActivityResponse]


# ==========================================
# STUDY CALENDAR SCHEMAS
# ==========================================

class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Optional task notes or outline")
    category: str = Field(default="General", description="Category: OS, DSA, DBMS, AI/ML, Revision, Exam Prep, Placement, General")
    task_date: str = Field(..., description="Date of the task in YYYY-MM-DD format")
    start_time: Optional[str] = Field(None, description="Optional start time, e.g. 14:00")
    end_time: Optional[str] = Field(None, description="Optional end time, e.g. 15:30")
    priority: str = Field(default="medium", description="Priority: low, medium, high")
    user_id: str = Field(default="demo-user", description="User identifier")


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    task_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    priority: Optional[str] = None
    is_completed: Optional[bool] = None


class TaskResponse(BaseModel):
    id: int
    user_id: str
    title: str
    description: Optional[str] = None
    category: str
    task_date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    priority: str
    is_completed: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CalendarMonthSummary(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    completion_rate: float


class CalendarTasksResponse(BaseModel):
    tasks: List[TaskResponse]
    summary: CalendarMonthSummary

