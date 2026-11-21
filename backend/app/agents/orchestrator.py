import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models import StudyPlan
from backend.app.agents.learner_profiler import LearnerProfilingAgent
from backend.app.agents.curriculum_planner import CurriculumPlannerAgent
from backend.app.agents.content_recommender import ContentRecommendationAgent
from backend.app.agents.quiz_agent import QuizAgent
from backend.app.agents.evaluation_agent import EvaluationAgent

logger = logging.getLogger("cloudlearn.agents.orchestrator")


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class LearningSystemOrchestrator:
    """
    Central Learning System Orchestrator
    -----------------------------------
    Coordinates the 5 specialized AI agents to power the mistake-to-mastery learning loop:
    1. Learner Profiling Agent -> Diagnoses proficiency & misconceptions
    2. Content Recommendation Agent -> Semantic search & grounding via Neon pgvector
    3. Curriculum Planner Agent -> Generates adaptive study plan
    4. Quiz Agent -> Generates RAG-grounded targeted quizzes
    5. Evaluation Agent -> Evaluates submissions & gap analysis
    """

    def __init__(self):
        self.profiler = LearnerProfilingAgent()
        self.recommender = ContentRecommendationAgent()
        self.planner = CurriculumPlannerAgent()
        self.quiz_agent = QuizAgent()
        self.evaluator = EvaluationAgent()

    def generate_study_plan(
        self,
        user_id: str,
        goal: str = "Master Core Computer Science & Technical Placements",
        target_timeline: str = "2 Weeks",
        focus_topics: Optional[List[str]] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Coordinates Profiler -> Recommender -> Planner to construct and persist
        an adaptive personalized study plan in Neon PostgreSQL.
        """
        trace = {
            "started_at": utc_now_iso(),
            "steps": [],
        }

        # Step 1: Profiler Agent
        logger.info(f"Orchestrator Step 1: Running {self.profiler.agent_name}")
        profile = self.profiler.analyze_profile(user_id=user_id, db=db)
        trace["steps"].append({
            "agent": self.profiler.agent_name,
            "action": "Diagnosed learner profile and identified misconceptions",
            "timestamp": utc_now_iso(),
            "summary": f"Identified {len(profile['weak_topics'])} weak topic(s) and {len(profile['mastered_topics'])} mastered topic(s)",
        })

        # Step 2: Content Recommendation Agent
        logger.info(f"Orchestrator Step 2: Running {self.recommender.agent_name}")
        recommendations = self.recommender.recommend_content(
            user_id=user_id,
            profile=profile,
            goal=goal,
            db=db,
        )
        trace["steps"].append({
            "agent": self.recommender.agent_name,
            "action": "Mapped weak topics and goal to indexed study documents in Neon pgvector",
            "timestamp": utc_now_iso(),
            "summary": f"Selected {len(recommendations['remediation_materials'])} remediation note(s) and {len(recommendations['curriculum_materials'])} curriculum reference(s)",
        })

        # Step 3: Curriculum Planner Agent
        logger.info(f"Orchestrator Step 3: Running {self.planner.agent_name}")
        raw_plan = self.planner.generate_study_plan(
            user_id=user_id,
            profile=profile,
            recommendations=recommendations,
            goal=goal,
            target_timeline=target_timeline,
            focus_topics=focus_topics,
        )
        trace["steps"].append({
            "agent": self.planner.agent_name,
            "action": "Synthesized 3-phase adaptive curriculum milestones",
            "timestamp": utc_now_iso(),
            "summary": f"Created {len(raw_plan['phases'])} phases with customized actionable milestones",
        })

        trace["completed_at"] = utc_now_iso()

        # Step 4: Persist Study Plan in Neon PostgreSQL
        plan_content = {
            "title": raw_plan["title"],
            "goal": goal,
            "target_timeline": target_timeline,
            "phases": raw_plan["phases"],
            "content_recommendations": recommendations.get("remediation_materials", []) + recommendations.get("curriculum_materials", [])[:4],
            "agent_trace": trace,
        }

        # Check if an active plan already exists and update or create
        existing_plan = (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id, StudyPlan.status == "active")
            .first()
        )

        if existing_plan:
            existing_plan.title = raw_plan["title"]
            existing_plan.goal = goal
            existing_plan.target_timeline = target_timeline
            existing_plan.plan_data = json.dumps(plan_content)
            db.commit()
            db.refresh(existing_plan)
            plan_record = existing_plan
        else:
            plan_record = StudyPlan(
                user_id=user_id,
                title=raw_plan["title"],
                goal=goal,
                target_timeline=target_timeline,
                status="active",
                plan_data=json.dumps(plan_content),
            )
            db.add(plan_record)
            db.commit()
            db.refresh(plan_record)

        return plan_record.to_dict()

    def get_active_study_plan(self, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Retrieves the user's active study plan from Neon PostgreSQL.
        """
        plan = (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id, StudyPlan.status == "active")
            .order_by(StudyPlan.updated_at.desc())
            .first()
        )
        if plan:
            return plan.to_dict()
        return None

    def update_milestone_status(
        self,
        user_id: str,
        milestone_id: str,
        new_status: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Updates the completion status of a specific milestone in the active study plan.
        """
        plan = (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id, StudyPlan.status == "active")
            .order_by(StudyPlan.updated_at.desc())
            .first()
        )
        if not plan:
            raise ValueError("No active study plan found for user.")

        data = json.loads(plan.plan_data)
        phases = data.get("phases", [])
        updated = False

        for phase in phases:
            for milestone in phase.get("milestones", []):
                if str(milestone.get("id")) == str(milestone_id):
                    milestone["status"] = new_status
                    updated = True
                    break
            if updated:
                break

        if not updated:
            raise ValueError(f"Milestone '{milestone_id}' not found in active study plan.")

        plan.plan_data = json.dumps(data)
        db.commit()
        db.refresh(plan)
        return plan.to_dict()

    def orchestrate_targeted_remediation(
        self,
        user_id: str,
        topic: Optional[str] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Coordinates Profiler -> Recommender -> Quiz Agent to generate a targeted remediation quiz.
        """
        profile = self.profiler.analyze_profile(user_id=user_id, db=db)
        weak_topics = profile.get("weak_topics", [])

        effective_topic = topic
        focus_concepts = []

        if not effective_topic:
            if weak_topics:
                effective_topic = weak_topics[0]["topic"]
                focus_concepts = weak_topics[0].get("missed_concepts", [])
            else:
                effective_topic = "Operating Systems"

        quiz = self.quiz_agent.generate_targeted_remediation_quiz(
            user_id=user_id,
            topic=effective_topic,
            focus_concepts=focus_concepts,
            num_questions=3,
            db=db,
        )

        return {
            "quiz": quiz,
            "targeted_topic": effective_topic,
            "targeted_concepts": focus_concepts,
            "orchestrated_by": "LearningSystemOrchestrator",
        }

    def orchestrate_quiz_evaluation(
        self,
        user_id: str,
        quiz_id: int,
        answers: Dict[str, Any],
        milestone_id: Optional[str] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Coordinates Evaluation Agent -> Study Plan update -> Diagnostic Gap Analysis.
        """
        eval_result = self.evaluator.evaluate_quiz(
            user_id=user_id,
            quiz_id=quiz_id,
            answers=answers,
            milestone_id=milestone_id,
            db=db,
        )

        # If a milestone was associated and student passed (>=66%), auto-update milestone
        updated_plan = None
        if milestone_id and eval_result.get("milestone_action") == "completed":
            try:
                updated_plan = self.update_milestone_status(
                    user_id=user_id,
                    milestone_id=milestone_id,
                    new_status="completed",
                    db=db,
                )
            except Exception as e:
                logger.warning(f"Could not update milestone status: {e}")

        return {
            "evaluation": eval_result,
            "updated_plan": updated_plan,
        }

    def get_agent_system_status(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Reports operational status and telemetry for all 5 agents.
        """
        profile = self.profiler.analyze_profile(user_id=user_id, db=db)
        active_plan = self.get_active_study_plan(user_id=user_id, db=db)

        agents_status = {
            "learner_profiling_agent": {
                "name": self.profiler.agent_name,
                "status": "ready",
                "role": "Diagnoses quiz performance, weak concepts, and learning velocity",
            },
            "curriculum_planner_agent": {
                "name": self.planner.agent_name,
                "status": "ready",
                "role": "Synthesizes adaptive multi-phase study plans from learner goals",
            },
            "content_recommendation_agent": {
                "name": self.recommender.agent_name,
                "status": "ready",
                "role": "Discovers and matches grounded notes excerpts via Neon pgvector",
            },
            "quiz_agent": {
                "name": self.quiz_agent.agent_name,
                "status": "ready",
                "role": "Generates grounded targeted MCQs and milestone practice",
            },
            "evaluation_agent": {
                "name": self.evaluator.agent_name,
                "status": "ready",
                "role": "Grades submissions, identifies knowledge gaps, and updates mastery",
            },
        }

        return {
            "orchestrator_status": "operational",
            "agents": agents_status,
            "active_plan": active_plan,
            "learner_profile_summary": {
                "overall_accuracy": profile.get("overall_accuracy", 0.0),
                "learning_tier": profile.get("learning_tier", "Developing"),
                "learning_velocity": profile.get("learning_velocity", "Steady"),
                "weak_topics_count": len(profile.get("weak_topics", [])),
                "mastered_topics_count": len(profile.get("mastered_topics", [])),
                "summary_narrative": profile.get("summary_narrative", ""),
            },
        }


# Singleton orchestrator instance
orchestrator = LearningSystemOrchestrator()

