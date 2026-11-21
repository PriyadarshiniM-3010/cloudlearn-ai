import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.services.quiz_service import evaluate_quiz_submission

logger = logging.getLogger("cloudlearn.agents.evaluator")


class EvaluationAgent:
    """
    Evaluation Agent
    ----------------
    Role: Evaluates quiz answers, performs deep misconception & knowledge gap analysis,
    updates topic mastery in Neon PostgreSQL, and determines milestone completion status.
    """

    def __init__(self):
        self.agent_name = "Evaluation Agent"
        self.version = "1.0.0"

    def evaluate_quiz(
        self,
        user_id: str,
        quiz_id: int,
        answers: Dict[str, Any],
        milestone_id: Optional[str] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Evaluates the student submission, updates LearningProgress in Neon,
        and produces a diagnostic gap analysis.
        """
        logger.info(f"EvaluationAgent grading quiz {quiz_id} for user {user_id}")

        # 1. Run core evaluation and database persistence
        eval_result = evaluate_quiz_submission(
            db=db,
            quiz_id=quiz_id,
            user_id=user_id,
            answers=answers,
        )

        results = eval_result.get("results", [])
        score = eval_result.get("score", 0)
        total = eval_result.get("total_questions", 1)
        percentage = eval_result.get("percentage", 0.0)

        # 2. Extract specific knowledge gaps and mastered concepts
        knowledge_gaps: List[Dict[str, Any]] = []
        mastered_concepts: List[str] = []

        for r in results:
            if r.get("is_correct"):
                mastered_concepts.append(r.get("question", "")[:80])
            else:
                knowledge_gaps.append({
                    "question_id": r.get("question_id"),
                    "concept": r.get("question", ""),
                    "student_choice": r.get("options", [])[r.get("selected_index")] if r.get("selected_index") is not None and 0 <= r.get("selected_index") < len(r.get("options", [])) else "Unanswered",
                    "correct_answer": r.get("options", [])[r.get("correct_index")] if 0 <= r.get("correct_index") < len(r.get("options", [])) else "Correct Option",
                    "explanation": r.get("explanation", ""),
                    "source_reference": r.get("source_reference", "Study Notes"),
                })

        # 3. Assess Milestone Completion (Pass threshold >= 66%)
        passed_milestone = percentage >= 66.0
        milestone_action = "none"
        if milestone_id:
            milestone_action = "completed" if passed_milestone else "remediation_required"

        # 4. Formulate pedagogical next steps
        if percentage >= 80.0:
            next_step = f"Excellent! You demonstrated comprehensive mastery ({percentage}%). Proceed to the next curriculum milestone or challenge topic."
        elif percentage >= 50.0:
            next_step = f"Good effort ({percentage}%). Review the {len(knowledge_gaps)} identified knowledge gap(s) before advancing to higher difficulty."
        else:
            next_step = f"Needs focused remediation ({percentage}%). Re-read your grounded notes on {knowledge_gaps[0]['concept'][:50] if knowledge_gaps else 'this topic'} and take a targeted practice quiz."

        return {
            "evaluating_agent": self.agent_name,
            "attempt_id": eval_result.get("attempt_id"),
            "quiz_id": quiz_id,
            "user_id": user_id,
            "score": score,
            "total_questions": total,
            "percentage": percentage,
            "mastery_status": eval_result.get("mastery_status"),
            "feedback": eval_result.get("feedback"),
            "knowledge_gaps": knowledge_gaps,
            "mastered_concepts": mastered_concepts,
            "next_pedagogical_action": next_step,
            "milestone_id": milestone_id,
            "milestone_action": milestone_action,
            "results": results,
            "created_at": eval_result.get("created_at"),
        }

