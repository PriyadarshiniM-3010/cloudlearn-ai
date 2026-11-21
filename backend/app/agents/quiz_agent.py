import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.services.quiz_service import generate_quiz, generate_targeted_quiz

logger = logging.getLogger("cloudlearn.agents.quiz_agent")


class QuizAgent:
    """
    Quiz Agent
    ----------
    Role: Generates targeted and milestone-based quizzes using Gemini and
    the Neon pgvector RAG pipeline, aligning questions with curriculum goals
    and remediation targets.
    """

    def __init__(self):
        self.agent_name = "Quiz Agent"
        self.version = "1.0.0"

    def generate_targeted_remediation_quiz(
        self,
        user_id: str,
        topic: str,
        focus_concepts: Optional[List[str]] = None,
        num_questions: int = 3,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Generates a targeted remediation quiz focused directly on the learner's
        identified misconceptions using RAG excerpts from uploaded notes.
        """
        logger.info(f"QuizAgent generating remediation quiz for {topic} (User: {user_id})")
        quiz = generate_targeted_quiz(
            db=db,
            topic=topic,
            focus_concepts=focus_concepts,
            num_questions=num_questions,
            user_id=user_id,
        )
        data = quiz.to_dict()
        data["generating_agent"] = self.agent_name
        data["quiz_type"] = "targeted_remediation"
        return data

    def generate_milestone_quiz(
        self,
        user_id: str,
        milestone_title: str,
        topic: str,
        action_type: str = "targeted_quiz",
        num_questions: int = 3,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Generates a quiz tailored to a specific study plan milestone.
        """
        logger.info(f"QuizAgent generating milestone quiz: {milestone_title}")
        difficulty = "advanced" if "synthesis" in milestone_title.lower() or "mock" in milestone_title.lower() else "intermediate"

        # Check if topic has targeted remediation focus
        if action_type == "targeted_quiz":
            quiz = generate_targeted_quiz(
                db=db,
                topic=topic,
                focus_concepts=[milestone_title],
                num_questions=num_questions,
                user_id=user_id,
            )
        else:
            quiz = generate_quiz(
                db=db,
                topic=topic,
                num_questions=num_questions,
                difficulty=difficulty,
                user_id=user_id,
            )

        data = quiz.to_dict()
        data["generating_agent"] = self.agent_name
        data["quiz_type"] = "curriculum_milestone"
        data["milestone_title"] = milestone_title
        return data

    def generate_document_quiz(
        self,
        user_id: str,
        document_id: int,
        num_questions: int = 5,
        difficulty: str = "intermediate",
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Generates a diagnostic quiz grounded directly in a specific study document.
        """
        logger.info(f"QuizAgent generating document quiz for doc {document_id}")
        quiz = generate_quiz(
            db=db,
            document_id=document_id,
            num_questions=num_questions,
            difficulty=difficulty,
            user_id=user_id,
        )
        data = quiz.to_dict()
        data["generating_agent"] = self.agent_name
        data["quiz_type"] = "document_grounded"
        return data

