import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models import StudyDocument, DocumentChunk
from backend.app.services.rag_service import search_relevant_chunks

logger = logging.getLogger("cloudlearn.agents.recommender")


class ContentRecommendationAgent:
    """
    Content Recommendation Agent
    ----------------------------
    Role: Analyzes learner misconceptions and study goals to recommend
    relevant uploaded notes, specific document pages, and grounded learning resources
    via Neon pgvector semantic search.
    """

    def __init__(self):
        self.agent_name = "Content Recommendation Agent"
        self.version = "1.0.0"

    def recommend_content(
        self,
        user_id: str,
        profile: Dict[str, Any],
        goal: str,
        db: Session,
        max_recommendations: int = 6,
    ) -> Dict[str, Any]:
        """
        Recommends high-yield study notes and exact chunks mapped to the learner's
        weak concepts and overall curriculum goal.
        """
        weak_topics = profile.get("weak_topics", [])
        remediation_materials: List[Dict[str, Any]] = []
        curriculum_materials: List[Dict[str, Any]] = []
        seen_doc_ids = set()

        # 1. Gather Remediation Materials for Identified Misconceptions
        for wt in weak_topics[:3]:
            topic = wt.get("topic", "")
            missed_concepts = wt.get("missed_concepts", [])
            query_str = f"{topic} " + " ".join(missed_concepts[:2]) if missed_concepts else topic

            try:
                chunks = search_relevant_chunks(
                    db=db,
                    query=query_str,
                    user_id=user_id,
                    top_k=3,
                )
                for chunk in chunks:
                    doc_id = chunk["document_id"]
                    remediation_materials.append({
                        "type": "remediation",
                        "topic": topic,
                        "document_id": doc_id,
                        "document_title": chunk["document_title"],
                        "document_filename": chunk["document_filename"],
                        "page_number": chunk["page_number"],
                        "relevance_score": chunk.get("similarity_score", chunk.get("similarity", 0.85)),
                        "snippet": chunk["content"][:240].strip() + "...",
                        "rationale": f"Directly targets your misconception in {topic} ({missed_concepts[0][:50]}...)" if missed_concepts else f"High-yield review for {topic}",
                    })
                    seen_doc_ids.add(doc_id)
            except Exception as e:
                logger.warning(f"Error retrieving RAG chunks for topic {topic}: {e}")

        # 2. Gather Curriculum Materials aligned with User Goal
        all_docs = (
            db.query(StudyDocument)
            .filter(StudyDocument.user_id == user_id)
            .all()
        )

        for doc in all_docs:
            is_remediation = doc.id in seen_doc_ids
            doc_topic = doc.topic or doc.title

            curriculum_materials.append({
                "type": "curriculum",
                "document_id": doc.id,
                "document_title": doc.title,
                "document_filename": doc.filename,
                "topic": doc_topic,
                "page_count": doc.page_count,
                "chunk_count": doc.chunk_count,
                "is_remediation_target": is_remediation,
                "rationale": f"Core revision resource for {doc_topic} matching goal '{goal}'",
            })

        # 3. Extract High-Yield Study Pointers from available materials
        study_pointers: List[str] = []
        for r in remediation_materials[:3]:
            study_pointers.append(f"Review {r['document_title']} (Page {r['page_number']}) on {r['topic']}")

        if not study_pointers:
            for doc in all_docs[:3]:
                study_pointers.append(f"Review core principles in {doc.title}")

        return {
            "agent": self.agent_name,
            "user_id": user_id,
            "goal": goal,
            "remediation_materials": remediation_materials[:max_recommendations],
            "curriculum_materials": curriculum_materials,
            "study_pointers": study_pointers,
            "total_notes_available": len(all_docs),
        }
