import json
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.models import QuizAttempt, Quiz, LearningProgress, StudyDocument

logger = logging.getLogger("cloudlearn.agents.profiler")


class LearnerProfilingAgent:
    """
    Learner Profiling Agent
    -----------------------
    Role: Analyzes learner quiz history, weak topics, mistake patterns, and progress
    to build a dynamic diagnostic profile of strengths, misconceptions, and learning velocity.
    """

    def __init__(self):
        self.agent_name = "Learner Profiling Agent"
        self.version = "1.0.0"

    def analyze_profile(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Synthesizes a deep diagnostic profile for the learner.
        """
        # 1. Fetch attempts and progress from Neon PostgreSQL
        attempts = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.created_at.asc())
            .all()
        )

        progress_records = (
            db.query(LearningProgress)
            .filter(LearningProgress.user_id == user_id)
            .all()
        )
        progress_by_topic = {p.topic.lower(): p for p in progress_records}

        uploaded_docs = (
            db.query(StudyDocument)
            .filter(StudyDocument.user_id == user_id)
            .all()
        )

        total_quizzes = len(attempts)
        total_questions = sum(a.total_questions for a in attempts)
        total_correct = sum(a.score for a in attempts)
        overall_accuracy = round((total_correct / total_questions) * 100, 1) if total_questions > 0 else 0.0

        # Group attempts by topic
        topic_attempts: Dict[str, List[QuizAttempt]] = {}
        for att in attempts:
            topic_name = att.quiz.topic if att.quiz and att.quiz.topic else "General"
            if topic_name not in topic_attempts:
                topic_attempts[topic_name] = []
            topic_attempts[topic_name].append(att)

        for p in progress_records:
            if p.topic not in topic_attempts:
                topic_attempts[p.topic] = []

        mastered_topics: List[Dict[str, Any]] = []
        in_progress_topics: List[Dict[str, Any]] = []
        weak_topics: List[Dict[str, Any]] = []

        # 2. Extract weak concepts and topic mastery
        for topic_name, att_list in topic_attempts.items():
            prog = progress_by_topic.get(topic_name.lower())

            q_count = sum(a.total_questions for a in att_list)
            corr_count = sum(a.score for a in att_list)

            if prog and prog.total_questions > q_count:
                q_count = prog.total_questions
                corr_count = prog.correct_answers

            mistakes = max(0, q_count - corr_count)
            score_pct = round((corr_count / q_count) * 100, 1) if q_count > 0 else 0.0

            # Gather all missed questions / concepts
            missed_concepts: List[str] = []
            for a in reversed(att_list):
                try:
                    ans_list = json.loads(a.answers_data)
                    for ans in ans_list:
                        if not ans.get("is_correct"):
                            q_txt = ans.get("question", "").strip()
                            if q_txt and q_txt not in missed_concepts:
                                missed_concepts.append(q_txt)
                except Exception:
                    pass

            # Fallback to last_mistake_summary if available
            if not missed_concepts and prog and prog.last_mistake_summary and "no mistakes" not in prog.last_mistake_summary.lower():
                missed_concepts.append(prog.last_mistake_summary)

            topic_info = {
                "topic": topic_name,
                "mastery_score": score_pct,
                "total_questions": q_count,
                "correct_answers": corr_count,
                "mistake_count": mistakes,
                "attempts_count": len(att_list),
                "missed_concepts": missed_concepts[:5],
                "last_active": att_list[-1].created_at.isoformat() if att_list and att_list[-1].created_at else None,
            }

            if score_pct >= 80.0 and mistakes <= 1:
                mastered_topics.append(topic_info)
            elif score_pct >= 50.0:
                in_progress_topics.append(topic_info)
            else:
                weak_topics.append(topic_info)

            # Also flag as weak if there are recent misconceptions even if total score is moderate
            if score_pct < 75.0 or mistakes > 0:
                if topic_info not in weak_topics:
                    weak_topics.append(topic_info)

        # Remove duplicates from weak_topics if present in both
        seen_weak = set()
        clean_weak_topics = []
        for wt in weak_topics:
            if wt["topic"] not in seen_weak:
                seen_weak.add(wt["topic"])
                clean_weak_topics.append(wt)
        weak_topics = sorted(clean_weak_topics, key=lambda x: (x["mastery_score"], -x["mistake_count"]))

        # 3. Compute learning tier and velocity
        if total_quizzes == 0:
            learning_tier = "New Learner"
            learning_velocity = "Ready to Begin"
        elif overall_accuracy >= 80.0:
            learning_tier = "Advanced Mastery"
        elif overall_accuracy >= 65.0:
            learning_tier = "Competent"
        elif overall_accuracy >= 45.0:
            learning_tier = "Developing"
        else:
            learning_tier = "Foundational Beginner"

        if total_quizzes < 2:
            learning_velocity = "Calibrating"
        else:
            mid = total_quizzes // 2
            older_avg = sum(a.percentage for a in attempts[:mid]) / max(1, mid)
            newer_avg = sum(a.percentage for a in attempts[mid:]) / max(1, total_quizzes - mid)
            if newer_avg >= older_avg + 5.0:
                learning_velocity = "Accelerating (Improving)"
            elif newer_avg <= older_avg - 5.0:
                learning_velocity = "Needs Reinforcement (Declining)"
            else:
                learning_velocity = "Steady"

        # 4. Generate summary narrative
        strengths = [t["topic"] for t in mastered_topics]
        weaknesses = [t["topic"] for t in weak_topics]
        doc_count = len(uploaded_docs)

        narrative_parts = []
        if strengths:
            narrative_parts.append(f"Demonstrated solid mastery in {', '.join(strengths[:3])}.")
        if weaknesses:
            narrative_parts.append(f"Requires targeted reinforcement in {', '.join(weaknesses[:3])}.")
        else:
            narrative_parts.append("Consistently strong performance across attempted subjects.")

        narrative_parts.append(
            f"Overall accuracy is {overall_accuracy}% across {total_questions} questions ({total_quizzes} quizzes). "
            f"Has {doc_count} indexed study document(s) available for grounding."
        )
        summary_narrative = " ".join(narrative_parts)

        return {
            "agent": self.agent_name,
            "user_id": user_id,
            "overall_accuracy": overall_accuracy,
            "total_quizzes_taken": total_quizzes,
            "total_questions_answered": total_questions,
            "total_correct_answers": total_correct,
            "mastered_topics": mastered_topics,
            "in_progress_topics": in_progress_topics,
            "weak_topics": weak_topics,
            "learning_tier": learning_tier,
            "learning_velocity": learning_velocity,
            "summary_narrative": summary_narrative,
            "uploaded_docs_count": doc_count,
        }

