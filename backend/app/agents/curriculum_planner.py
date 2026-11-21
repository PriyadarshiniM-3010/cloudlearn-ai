import json
import logging
import re
from typing import Dict, Any, List, Optional

from backend.app.services.gemini_service import call_gemini_robust

logger = logging.getLogger("cloudlearn.agents.planner")


class CurriculumPlannerAgent:
    """
    Curriculum Planner Agent
    ------------------------
    Role: Creates an adaptive, personalized multi-phase study plan based on
    the learner's diagnostic profile, target goals, and performance trajectory.
    """

    def __init__(self):
        self.agent_name = "Curriculum Planner Agent"
        self.version = "1.0.0"

    def generate_study_plan(
        self,
        user_id: str,
        profile: Dict[str, Any],
        recommendations: Dict[str, Any],
        goal: str = "Master Core Computer Science & Technical Placements",
        target_timeline: str = "2 Weeks",
        focus_topics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a personalized, phased study plan with actionable milestones.
        """
        weak_topics = profile.get("weak_topics", [])
        mastered_topics = profile.get("mastered_topics", [])
        remediation_docs = recommendations.get("remediation_materials", [])
        curriculum_docs = recommendations.get("curriculum_materials", [])

        # Build context prompt for Gemini
        system_instruction = """You are CloudLearn AI's Curriculum Planner Agent.
Your mission is to construct an adaptive, high-impact personalized study plan for a computer science learner.

Follow this 3-Phase Pedagogical Structure:
- Phase 1: Targeted Remediation (Fix immediate conceptual gaps and mistakes from past quizzes)
- Phase 2: Core Concept Mastery (Deepen understanding of foundational topics and unquizzed notes)
- Phase 3: Synthesis & Placement Readiness (Advanced problem solving, mock evaluations)

REQUIREMENTS:
1. Each phase MUST contain 2 to 3 concrete, actionable milestones.
2. Every milestone must have:
   - id: unique string, e.g. "m1_1", "m1_2"
   - phase: name of phase
   - title: clear actionable milestone title
   - topic: subject name
   - action_type: one of ["review_notes", "targeted_quiz", "concept_deep_dive", "comprehensive_test"]
   - description: clear explanation of what to review and what misconception to solve
   - estimated_minutes: realistic duration in minutes (e.g. 20, 30, 45)
   - recommended_doc_title: title of relevant uploaded note if available, else generic
   - status: "pending"
3. Directly reference the student's actual weak topics and past mistakes in Phase 1!

OUTPUT FORMAT:
Return pure, valid JSON with no markdown formatting or fences:
{
  "title": "Personalized CS Placement & Concept Mastery Plan",
  "goal": "...",
  "target_timeline": "...",
  "phases": [
    {
      "phase_name": "Phase 1: Targeted Remediation & Gap Filling",
      "focus": "Overcome recurring misconceptions in ...",
      "milestones": [
        {
          "id": "m1_1",
          "phase": "Phase 1",
          "title": "Remediate Operating Systems Deadlock Conditions",
          "topic": "Operating Systems",
          "action_type": "review_notes",
          "description": "Review Coffman conditions and resource allocation graphs to resolve deadlock traps.",
          "recommended_doc_title": "Operating Systems Lecture Notes",
          "estimated_minutes": 25,
          "status": "pending"
        }
      ]
    }
  ]
}
"""

        weak_summary = []
        for wt in weak_topics:
            concepts = ", ".join(wt.get("missed_concepts", [])[:2])
            weak_summary.append(f"- {wt['topic']} (Mastery: {wt['mastery_score']}%, Missed: {concepts})")
        weak_str = "\n".join(weak_summary) if weak_summary else "No critical weak topics identified yet."

        mastered_summary = [f"- {mt['topic']} ({mt['mastery_score']}%)" for mt in mastered_topics]
        mastered_str = "\n".join(mastered_summary) if mastered_summary else "None yet."

        notes_summary = [f"- {d['document_title']} (Topic: {d['topic']})" for d in curriculum_docs[:6]]
        notes_str = "\n".join(notes_summary) if notes_summary else "General computer science curriculum."

        prompt = f"""
LEARNER DIAGNOSTIC PROFILE:
===========================
User ID: {user_id}
Goal: {goal}
Timeline: {target_timeline}
Overall Accuracy: {profile.get('overall_accuracy', 0.0)}%
Learning Tier: {profile.get('learning_tier', 'Developing')}
Velocity: {profile.get('learning_velocity', 'Steady')}

WEAK TOPICS & IDENTIFIED GAPS:
{weak_str}

ALREADY MASTERED TOPICS:
{mastered_str}

AVAILABLE STUDY NOTES (FOR GROUNDING):
{notes_str}

OPTIONAL FOCUS TOPICS:
{', '.join(focus_topics) if focus_topics else 'Balanced comprehensive curriculum'}

Generate the structured JSON study plan now.
"""

        plan_data: Optional[Dict[str, Any]] = None
        try:
            res = call_gemini_robust(prompt=prompt, system_instruction=system_instruction)
            raw = res["answer"].strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                plan_data = json.loads(match.group(0))
        except Exception as e:
            logger.warning(f"CurriculumPlanner Gemini generation failed or timed out: {e}. Falling back to deterministic plan.")

        # Deterministic Fallback if LLM output was invalid
        if not plan_data or not plan_data.get("phases"):
            plan_data = self._generate_deterministic_plan(
                profile=profile,
                recommendations=recommendations,
                goal=goal,
                target_timeline=target_timeline,
            )

        # Standardize phases and milestones
        sanitized_phases: List[Dict[str, Any]] = []
        for p_idx, phase in enumerate(plan_data.get("phases", [])):
            p_name = phase.get("phase_name", f"Phase {p_idx + 1}")
            p_focus = phase.get("focus", "Conceptual reinforcement and practice")
            sanitized_milestones: List[Dict[str, Any]] = []

            for m_idx, m in enumerate(phase.get("milestones", [])):
                m_id = m.get("id") or f"m{p_idx + 1}_{m_idx + 1}"
                sanitized_milestones.append({
                    "id": str(m_id),
                    "phase": p_name,
                    "title": str(m.get("title", f"Milestone {p_idx + 1}.{m_idx + 1}")),
                    "topic": str(m.get("topic", "Computer Science")),
                    "action_type": str(m.get("action_type", "targeted_quiz")),
                    "description": str(m.get("description", "Review concepts and complete targeted self-assessment.")),
                    "recommended_doc_title": m.get("recommended_doc_title") or (curriculum_docs[0]["document_title"] if curriculum_docs else None),
                    "recommended_doc_id": m.get("recommended_doc_id"),
                    "estimated_minutes": int(m.get("estimated_minutes", 30)),
                    "status": m.get("status", "pending"),
                })

            sanitized_phases.append({
                "phase_name": p_name,
                "focus": p_focus,
                "milestones": sanitized_milestones,
            })

        return {
            "agent": self.agent_name,
            "title": plan_data.get("title", f"Personalized Study Plan: {goal}"),
            "goal": goal,
            "target_timeline": target_timeline,
            "status": "active",
            "phases": sanitized_phases,
        }

    def _generate_deterministic_plan(
        self,
        profile: Dict[str, Any],
        recommendations: Dict[str, Any],
        goal: str,
        target_timeline: str,
    ) -> Dict[str, Any]:
        """
        Robust deterministic curriculum builder derived from actual student performance.
        """
        weak_topics = profile.get("weak_topics", [])
        curriculum_docs = recommendations.get("curriculum_materials", [])

        primary_weak = weak_topics[0]["topic"] if weak_topics else "Operating Systems"
        secondary_weak = weak_topics[1]["topic"] if len(weak_topics) > 1 else "Database Management (DBMS)"

        phase1_milestones = [
            {
                "id": "m1_1",
                "phase": "Phase 1: Targeted Remediation",
                "title": f"Review & Remediate {primary_weak}",
                "topic": primary_weak,
                "action_type": "review_notes",
                "description": f"Target specific misconceptions and missed questions identified in {primary_weak}.",
                "recommended_doc_title": curriculum_docs[0]["document_title"] if curriculum_docs else "Core Notes",
                "estimated_minutes": 30,
                "status": "pending",
            },
            {
                "id": "m1_2",
                "phase": "Phase 1: Targeted Remediation",
                "title": f"Take Targeted Remediation Quiz on {primary_weak}",
                "topic": primary_weak,
                "action_type": "targeted_quiz",
                "description": f"Verify misconception resolution with 3 targeted MCQs on {primary_weak}.",
                "recommended_doc_title": curriculum_docs[0]["document_title"] if curriculum_docs else "Core Notes",
                "estimated_minutes": 20,
                "status": "pending",
            },
        ]

        phase2_milestones = [
            {
                "id": "m2_1",
                "phase": "Phase 2: Core Concept Mastery",
                "title": f"Deep Dive into {secondary_weak}",
                "topic": secondary_weak,
                "action_type": "concept_deep_dive",
                "description": f"Review core principles, schema models, and indexing strategies in {secondary_weak}.",
                "recommended_doc_title": curriculum_docs[1]["document_title"] if len(curriculum_docs) > 1 else "Core Notes",
                "estimated_minutes": 40,
                "status": "pending",
            },
            {
                "id": "m2_2",
                "phase": "Phase 2: Core Concept Mastery",
                "title": f"Assess Comprehension in {secondary_weak}",
                "topic": secondary_weak,
                "action_type": "targeted_quiz",
                "description": "Benchmark retention with 5 core concept questions.",
                "recommended_doc_title": curriculum_docs[1]["document_title"] if len(curriculum_docs) > 1 else "Core Notes",
                "estimated_minutes": 25,
                "status": "pending",
            },
        ]

        phase3_milestones = [
            {
                "id": "m3_1",
                "phase": "Phase 3: Placement Synthesis & Readiness",
                "title": "Comprehensive Multi-Topic Mock Exam",
                "topic": "Comprehensive Computer Science",
                "action_type": "comprehensive_test",
                "description": f"Full placement simulation testing cross-cutting concepts for goal '{goal}'.",
                "recommended_doc_title": "All Indexed Notes",
                "estimated_minutes": 45,
                "status": "pending",
            }
        ]

        return {
            "title": f"Personalized Curriculum Plan: {goal}",
            "goal": goal,
            "target_timeline": target_timeline,
            "phases": [
                {
                    "phase_name": "Phase 1: Targeted Remediation & Gap Repair",
                    "focus": f"Repair immediate misconceptions in {primary_weak}",
                    "milestones": phase1_milestones,
                },
                {
                    "phase_name": "Phase 2: Core Concept Expansion",
                    "focus": f"Master foundational principles in {secondary_weak}",
                    "milestones": phase2_milestones,
                },
                {
                    "phase_name": "Phase 3: Synthesis & Placement Readiness",
                    "focus": "Synthesize all curriculum domains and verify exam readiness",
                    "milestones": phase3_milestones,
                },
            ],
        }

