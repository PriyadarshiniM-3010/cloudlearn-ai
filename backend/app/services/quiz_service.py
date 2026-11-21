import json
import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models import Quiz, QuizAttempt, StudyDocument, DocumentChunk, LearningProgress
from backend.app.services.gemini_service import call_gemini_robust

logger = logging.getLogger("cloudlearn.quiz")


def clean_options_list(options: Any) -> List[str]:
    """
    Sanitizes option lists returned by LLM, handling nested lists,
    stringified lists, and letter prefixes ('A)', '1.').
    """
    if isinstance(options, str):
        try:
            parsed = json.loads(options)
            if isinstance(parsed, list):
                options = parsed
        except Exception:
            try:
                import ast
                parsed = ast.literal_eval(options)
                if isinstance(parsed, list):
                    options = parsed
            except Exception:
                pass

    if isinstance(options, list) and len(options) == 1 and isinstance(options[0], list):
        options = options[0]

    # Handle case where LLM returned array of 4 items where each item is stringified list
    if isinstance(options, list) and len(options) > 0 and isinstance(options[0], str) and options[0].strip().startswith("["):
        try:
            import ast
            parsed = ast.literal_eval(options[0].strip())
            if isinstance(parsed, list) and len(parsed) >= 4:
                options = parsed
        except Exception:
            pass

    if not isinstance(options, list) or len(options) < 4:
        return []

    cleaned = []
    for opt in options[:4]:
        s = str(opt).strip()
        s = re.sub(r"^[A-Da-d1-4][\.\)]\s*", "", s).strip()
        s = re.sub(r"^['\"]|['\"]$", "", s).strip()
        cleaned.append(s)

    return cleaned if len(cleaned) == 4 else []


def robust_parse_quiz_json(raw_text: str, default_topic: str = "Computer Science", num_questions: int = 3) -> List[Dict[str, Any]]:
    """
    Tolerantly parses JSON quiz responses from LLM, auto-repairing missing commas,
    markdown fences, or malformed arrays, and guarantees valid questions.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    parsed = None
    try:
        parsed = json.loads(cleaned)
    except Exception:
        # Attempt auto-repairs for common LLM JSON syntax omissions
        repaired = cleaned
        repaired = re.sub(r',\s*([\]}])', r'\1', repaired)  # trailing commas
        repaired = re.sub(r'("\s*\n\s*")', '",\n"', repaired)
        repaired = re.sub(r'(\d+|true|false|null)\s*\n\s*"', r'\1,\n"', repaired)
        repaired = re.sub(r'(\})\s*\n\s*(\{)', r'\1,\n\2', repaired)
        try:
            parsed = json.loads(repaired)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except Exception:
                    pass

    raw_questions = []
    if isinstance(parsed, dict):
        raw_questions = parsed.get("questions", [])
    elif isinstance(parsed, list):
        raw_questions = parsed

    # If still no questions, regex search for individual question blocks
    if not raw_questions:
        blocks = re.findall(r'\{\s*"question".*?"explanation".*?\}', cleaned, re.DOTALL)
        for b in blocks:
            try:
                q_obj = json.loads(b)
                raw_questions.append(q_obj)
            except Exception:
                pass

    validated = []
    for idx, q in enumerate(raw_questions[:num_questions]):
        q_text = str(q.get("question", "")).strip()
        opts = clean_options_list(q.get("options", []))
        if len(opts) < 4:
            continue
        c_idx = q.get("correct_index")
        if c_idx is None or not (0 <= int(c_idx) < 4):
            ans_str = str(q.get("correct_answer", "")).upper()
            mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
            c_idx = mapping.get(ans_str, 0)
        else:
            c_idx = int(c_idx)

        exp = str(q.get("explanation", f"Option {chr(65 + c_idx)} is the correct answer.")).strip()
        src = str(q.get("source_reference", default_topic)).strip()

        validated.append({
            "id": idx + 1,
            "question": q_text,
            "options": opts,
            "correct_index": c_idx,
            "correct_answer": chr(65 + c_idx),
            "explanation": exp,
            "source_reference": src,
        })

    # High-yield fallback if LLM produced unparseable structure
    if not validated:
        logger.warning(f"Using high-yield targeted fallback questions for topic: {default_topic}")
        validated = [
            {
                "id": 1,
                "question": f"Which principle is central to correct operation and resource management in {default_topic}?",
                "options": [
                    f"Enforcing mutual exclusion and invariant checks across state transitions",
                    f"Bypassing synchronization checks for higher single-threaded throughput",
                    f"Relying solely on hardware interrupts without operating system validation",
                    f"Eliminating secondary storage caching entirely"
                ],
                "correct_index": 0,
                "correct_answer": "A",
                "explanation": f"In {default_topic}, mutual exclusion and invariant verification prevent race conditions and illegal memory/state corruption.",
                "source_reference": f"{default_topic} Core Principles"
            },
            {
                "id": 2,
                "question": f"When diagnosing performance degradation or deadlock conditions in {default_topic}, what is the recommended practice?",
                "options": [
                    f"Restarting all active processes immediately without inspecting wait-for graphs",
                    f"Constructing a resource-allocation graph to detect circular waits and lock-ordering violations",
                    f"Disabling all virtual memory page table mappings",
                    f"Increasing thread priority indefinitely"
                ],
                "correct_index": 1,
                "correct_answer": "B",
                "explanation": "Resource-allocation graphs and cycle detection directly identify deadlock (circular wait) and contention hotspots.",
                "source_reference": f"{default_topic} Lecture Notes"
            }
        ]

    return validated[:num_questions]


def generate_quiz(
    db: Session,
    topic: Optional[str] = None,
    document_id: Optional[int] = None,
    num_questions: int = 5,
    difficulty: str = "intermediate",
    user_id: str = "demo-user",
) -> Quiz:
    """
    Generates an AI multiple-choice quiz (MCQ) from uploaded study notes
    or from a domain topic using Gemini.
    Stores the quiz in Neon PostgreSQL and returns the Quiz model.
    """
    num_questions = max(1, min(10, num_questions))
    difficulty = difficulty.lower() if difficulty in ["beginner", "intermediate", "advanced"] else "intermediate"

    doc: Optional[StudyDocument] = None
    context_chunks = []
    quiz_title = ""
    effective_topic = topic or "General Computer Science"

    # 1. Gather context from document if document_id is specified
    if document_id:
        doc = db.query(StudyDocument).filter(StudyDocument.id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID {document_id} not found.")

        effective_topic = doc.topic or topic or "General"
        quiz_title = f"Quiz: {doc.title} ({difficulty.capitalize()})"

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        context_chunks = [f"[Page {c.page_number}]: {c.content}" for c in chunks[:12]]
    elif topic:
        quiz_title = f"Quiz: {topic} ({difficulty.capitalize()})"
        # Optionally find any related uploaded documents to enrich context
        matching_docs = (
            db.query(StudyDocument)
            .filter(StudyDocument.topic.ilike(f"%{topic}%"), StudyDocument.user_id == user_id)
            .all()
        )
        if matching_docs:
            doc_ids = [d.id for d in matching_docs]
            chunks = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id.in_(doc_ids))
                .order_by(DocumentChunk.chunk_index.asc())
                .limit(8)
                .all()
            )
            context_chunks = [f"[{c.document.title} | Page {c.page_number}]: {c.content}" for c in chunks]
    else:
        quiz_title = f"Quiz: Computer Science Fundamentals ({difficulty.capitalize()})"

    if context_chunks:
        context_text = "\n\n---\n\n".join(context_chunks)
        source_instruction = (
            "GROUNDING REQUIREMENT: Generate questions based directly on the provided study notes context. "
            "For each question, cite the exact source reference (e.g. document title and page number)."
        )
    else:
        context_text = "No uploaded study notes provided. Generate based on core placement/interview curriculum."
        source_instruction = "Generate rigorous, accurate multiple choice questions matching the topic and difficulty."

    system_instruction = f"""You are CloudLearn AI's Master Quiz Generator.
Your job is to generate exactly {num_questions} high-yield multiple-choice questions (MCQs) for engineering students.

REQUIREMENTS:
1. Difficulty Level: {difficulty.upper()}.
2. Subject/Topic: {effective_topic}.
3. Each question MUST have EXACTLY 4 distinct, plausible options: Option A, B, C, D.
4. Exactly ONE option must be completely correct.
5. Distractors (wrong options) must be realistic and reflect common student mistakes or subtle edge cases.
6. Provide a thorough pedagogical explanation for why the correct option is right and why the other options are wrong.
7. {source_instruction}

OUTPUT FORMAT:
You MUST respond with a single valid JSON object containing an array called "questions". Do not include markdown codeblocks or extra text.

Example format:
{{
  "questions": [
    {{
      "id": 1,
      "question": "What is the primary difference between paging and segmentation?",
      "options": [
        "Paging uses fixed-size memory blocks while segmentation uses variable-size logical units",
        "Paging is implemented purely in software while segmentation requires no hardware",
        "Paging prevents internal fragmentation while segmentation prevents external fragmentation",
        "Paging divides CPU registers into frames while segmentation divides RAM into pages"
      ],
      "correct_index": 0,
      "correct_answer": "A",
      "explanation": "Paging divides physical memory into fixed-size frames and virtual memory into fixed-size pages. Segmentation divides memory into variable-sized units reflecting the programmer's logical view.",
      "source_reference": "OS Paging Notes, Page 1"
    }}
  ]
}}
"""

    prompt = f"""
STUDY NOTES CONTEXT:
====================
{context_text}
====================

Generate {num_questions} multiple choice questions now. Return pure JSON.
"""

    gen_res = call_gemini_robust(prompt=prompt, system_instruction=system_instruction)
    raw_answer = gen_res["answer"].strip()

    # Clean markdown fences if any
    cleaned_json = raw_answer
    if cleaned_json.startswith("```"):
        cleaned_json = re.sub(r"^```(?:json)?\s*", "", cleaned_json)
        cleaned_json = re.sub(r"\s*```$", "", cleaned_json)

    try:
        parsed = json.loads(cleaned_json)
        raw_questions = parsed.get("questions", [])
    except Exception as e:
        logger.error(f"Failed to parse quiz JSON from Gemini: {e}. Raw text: {raw_answer[:300]}")
        # Try finding JSON block with regex
        match = re.search(r"\{.*\}", cleaned_json, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            raw_questions = parsed.get("questions", [])
        else:
            raise RuntimeError(f"Could not parse valid quiz JSON from Gemini response: {str(e)}")

    if not raw_questions:
        raise RuntimeError("Gemini did not return any quiz questions. Please try again.")

    # Validate and standardize questions
    validated_questions: List[Dict[str, Any]] = []
    for idx, q in enumerate(raw_questions[:num_questions]):
        q_text = str(q.get("question", "")).strip()
        clean_options = clean_options_list(q.get("options", []))
        if len(clean_options) < 4:
            continue

        correct_idx = q.get("correct_index")
        if correct_idx is None or not (0 <= int(correct_idx) < 4):
            # Check correct_answer string ('A', 'B', 'C', 'D')
            ans_str = str(q.get("correct_answer", "")).upper()
            mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
            correct_idx = mapping.get(ans_str, 0)
        else:
            correct_idx = int(correct_idx)

        explanation = str(q.get("explanation", f"Option {chr(65 + correct_idx)} is the correct answer.")).strip()
        src_ref = str(q.get("source_reference", doc.title if doc else effective_topic)).strip()

        validated_questions.append({
            "id": idx + 1,
            "question": q_text,
            "options": clean_options,
            "correct_index": correct_idx,
            "correct_answer": chr(65 + correct_idx),
            "explanation": explanation,
            "source_reference": src_ref,
        })

    if not validated_questions:
        raise RuntimeError("No valid questions could be structured from Gemini. Please try again.")

    # Save Quiz to Neon PostgreSQL
    quiz_record = Quiz(
        user_id=user_id,
        title=quiz_title,
        topic=effective_topic,
        document_id=document_id,
        difficulty=difficulty,
        total_questions=len(validated_questions),
        questions_data=json.dumps(validated_questions),
    )
    db.add(quiz_record)
    db.commit()
    db.refresh(quiz_record)

    return quiz_record


def evaluate_quiz_submission(
    db: Session,
    quiz_id: int,
    user_id: str,
    answers: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates student quiz answers, calculates percentage, logs mistakes,
    persists the attempt in Neon PostgreSQL, and updates the student's LearningProgress.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise ValueError(f"Quiz with ID {quiz_id} not found.")

    try:
        questions: List[Dict[str, Any]] = json.loads(quiz.questions_data)
    except Exception as e:
        raise RuntimeError(f"Could not load questions for quiz {quiz_id}: {str(e)}")

    score = 0
    total = len(questions)
    results = []
    mistakes_summary = []

    for q in questions:
        q_id = str(q["id"])
        # Support either string or integer keys from answers dict
        user_choice = answers.get(q_id)
        if user_choice is None:
            user_choice = answers.get(int(q_id))

        selected_idx = int(user_choice) if user_choice is not None else None
        correct_idx = q["correct_index"]
        is_correct = (selected_idx == correct_idx)

        if is_correct:
            score += 1
        else:
            mistakes_summary.append(f"Q{q['id']}: {q['question'][:60]}")

        results.append({
            "question_id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "selected_index": selected_idx,
            "correct_index": correct_idx,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "source_reference": q.get("source_reference", quiz.topic),
        })

    percentage = round((score / total) * 100, 1) if total > 0 else 0.0

    if percentage >= 80.0:
        mastery_status = "mastered"
        feedback = f"🎉 Outstanding performance! You demonstrated mastery with {score}/{total} correct ({percentage}%)."
    elif percentage >= 50.0:
        mastery_status = "in_progress"
        feedback = f"👍 Good effort! You scored {score}/{total} ({percentage}%). Review the questions marked below to consolidate your understanding."
    else:
        mastery_status = "needs_review"
        feedback = f"📚 Needs review! You scored {score}/{total} ({percentage}%). Check the explanations and review your study notes on this topic."

    # Save QuizAttempt to Neon PostgreSQL
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user_id,
        score=score,
        total_questions=total,
        percentage=percentage,
        answers_data=json.dumps(results),
        feedback=feedback,
    )
    db.add(attempt)

    # Update student's LearningProgress in Neon PostgreSQL
    progress = (
        db.query(LearningProgress)
        .filter(LearningProgress.user_id == user_id, LearningProgress.topic == quiz.topic)
        .first()
    )

    mistake_note = "; ".join(mistakes_summary[:3]) if mistakes_summary else "No mistakes on this attempt!"

    if progress:
        progress.total_questions += total
        progress.correct_answers += score
        progress.mistake_count += (total - score)
        if progress.total_questions > 0:
            progress.mastery_score = round((progress.correct_answers / progress.total_questions) * 100, 1)
        progress.last_mistake_summary = mistake_note
        progress.status = "mastered" if progress.mastery_score >= 80.0 else ("in_progress" if progress.mastery_score >= 50.0 else "needs_review")
    else:
        progress = LearningProgress(
            user_id=user_id,
            topic=quiz.topic,
            subtopic=quiz.title[:100],
            total_questions=total,
            correct_answers=score,
            mistake_count=total - score,
            mastery_score=percentage,
            last_mistake_summary=mistake_note,
            status=mastery_status,
        )
        db.add(progress)

    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": attempt.id,
        "quiz_id": quiz.id,
        "user_id": user_id,
        "score": score,
        "total_questions": total,
        "percentage": percentage,
        "results": results,
        "feedback": feedback,
        "mastery_status": mastery_status,
        "created_at": attempt.created_at.isoformat() if attempt.created_at else None,
    }


def get_quiz_by_id(db: Session, quiz_id: int) -> Optional[Quiz]:
    return db.query(Quiz).filter(Quiz.id == quiz_id).first()


def list_quizzes(db: Session, user_id: str = "demo-user", limit: int = 20) -> List[Quiz]:
    return (
        db.query(Quiz)
        .filter(Quiz.user_id == user_id)
        .order_by(Quiz.created_at.desc())
        .limit(limit)
        .all()
    )


def list_quiz_attempts(db: Session, user_id: str = "demo-user", limit: int = 20) -> List[QuizAttempt]:
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(limit)
        .all()
    )


def generate_targeted_quiz(
    db: Session,
    topic: str,
    focus_concepts: Optional[List[str]] = None,
    num_questions: int = 3,
    user_id: str = "demo-user",
) -> Quiz:
    """
    Generates a targeted remediation quiz focused on specific weak concepts or
    recurring mistakes for a student, grounded in their uploaded notes via RAG.
    """
    num_questions = max(1, min(10, num_questions))
    target_topic = topic.strip()

    # 1. Gather missed concepts from prior attempts if not explicitly passed
    extracted_concepts: List[str] = list(focus_concepts) if focus_concepts else []
    if not extracted_concepts:
        # Look for past attempts on this topic
        attempts = (
            db.query(QuizAttempt)
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
            .filter(QuizAttempt.user_id == user_id, Quiz.topic.ilike(f"%{target_topic}%"))
            .order_by(QuizAttempt.created_at.desc())
            .limit(5)
            .all()
        )
        for att in attempts:
            try:
                ans_list = json.loads(att.answers_data)
                for ans in ans_list:
                    if not ans.get("is_correct"):
                        q_txt = ans.get("question", "")
                        if q_txt and q_txt[:80] not in extracted_concepts:
                            extracted_concepts.append(q_txt[:80])
            except Exception:
                pass

    # 2. Retrieve relevant notes chunks using RAG
    search_query = f"{target_topic} " + " ".join(extracted_concepts[:3])
    retrieved_chunks = []
    try:
        from backend.app.services.rag_service import search_relevant_chunks
        chunks_res = search_relevant_chunks(
            db=db,
            query=search_query,
            user_id=user_id,
            top_k=5,
        )
        if chunks_res:
            retrieved_chunks = [
                f"[{c['document_title']} | Page {c['page_number']}]: {c['content']}"
                for c in chunks_res
            ]
    except Exception as e:
        logger.warning(f"RAG search failed in generate_targeted_quiz: {e}")

    # Fallback chunk gathering if vector search returned nothing
    if not retrieved_chunks:
        matching_docs = (
            db.query(StudyDocument)
            .filter(StudyDocument.topic.ilike(f"%{target_topic}%"))
            .all()
        )
        if matching_docs:
            doc_ids = [d.id for d in matching_docs]
            chunks = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id.in_(doc_ids))
                .order_by(DocumentChunk.chunk_index.asc())
                .limit(6)
                .all()
            )
            retrieved_chunks = [f"[{c.document.title} | Page {c.page_number}]: {c.content}" for c in chunks]

    if retrieved_chunks:
        context_text = "\n\n---\n\n".join(retrieved_chunks)
        source_instruction = (
            "GROUNDING REQUIREMENT: Ground each question directly in the provided study notes context. "
            "Cite the specific document and page reference in the source_reference field."
        )
    else:
        context_text = f"Curriculum topic: {target_topic}."
        source_instruction = "Generate rigorous conceptual practice questions targeting the specified misconceptions."

    concepts_str = ", ".join(extracted_concepts[:5]) if extracted_concepts else target_topic

    system_instruction = f"""You are CloudLearn AI's Targeted Remediation Quiz Generator.
Your mission is to turn student mistakes into mastery.
The student has shown misconceptions or requested targeted reinforcement on:
{concepts_str}

REQUIREMENTS:
1. Generate exactly {num_questions} multiple-choice questions targeting these exact weak concepts/misconceptions.
2. Each question MUST have EXACTLY 4 distinct options: Option A, B, C, D.
3. Exactly ONE option must be completely correct.
4. Distractors (wrong options) should specifically target common false assumptions or mistakes students make on this topic.
5. In the "explanation" field, explicitly address WHY common wrong answers are incorrect, clarifying the core concept so the student learns from the mistake.
6. {source_instruction}

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this schema. No markdown fences or commentary:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Question text here...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "correct_answer": "A",
      "explanation": "Detailed pedagogical explanation dispelling the misconception...",
      "source_reference": "Document / topic reference"
    }}
  ]
}}
"""

    prompt = f"""
STUDY NOTES CONTEXT:
====================
{context_text}
====================

WEAK CONCEPTS TO TARGET:
========================
{concepts_str}
========================

Generate {num_questions} targeted remediation MCQs now. Return pure JSON.
"""

    gen_res = call_gemini_robust(prompt=prompt, system_instruction=system_instruction)
    raw_answer = gen_res["answer"].strip()

    cleaned_json = raw_answer
    if cleaned_json.startswith("```"):
        cleaned_json = re.sub(r"^```(?:json)?\s*", "", cleaned_json)
        cleaned_json = re.sub(r"\s*```$", "", cleaned_json)

    try:
        parsed = json.loads(cleaned_json)
        raw_questions = parsed.get("questions", [])
    except Exception as e:
        match = re.search(r"\{.*\}", cleaned_json, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            raw_questions = parsed.get("questions", [])
        else:
            raise RuntimeError(f"Could not parse targeted quiz JSON: {str(e)}")

    if not raw_questions:
        raise RuntimeError("Gemini did not return any targeted quiz questions.")

    validated_questions: List[Dict[str, Any]] = []
    for idx, q in enumerate(raw_questions[:num_questions]):
        q_text = str(q.get("question", "")).strip()
        clean_options = clean_options_list(q.get("options", []))
        if len(clean_options) < 4:
            continue

        correct_idx = q.get("correct_index")
        if correct_idx is None or not (0 <= int(correct_idx) < 4):
            ans_str = str(q.get("correct_answer", "")).upper()
            mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
            correct_idx = mapping.get(ans_str, 0)
        else:
            correct_idx = int(correct_idx)

        explanation = str(q.get("explanation", f"Option {chr(65 + correct_idx)} is the correct answer.")).strip()
        src_ref = str(q.get("source_reference", target_topic)).strip()

        validated_questions.append({
            "id": idx + 1,
            "question": q_text,
            "options": clean_options,
            "correct_index": correct_idx,
            "correct_answer": chr(65 + correct_idx),
            "explanation": explanation,
            "source_reference": src_ref,
        })

    if not validated_questions:
        raise RuntimeError("No valid targeted questions could be parsed.")

    # Save to Neon PostgreSQL
    quiz_record = Quiz(
        user_id=user_id,
        title=f"🎯 Targeted Practice: {target_topic}",
        topic=target_topic,
        document_id=None,
        difficulty="intermediate",
        total_questions=len(validated_questions),
        questions_data=json.dumps(validated_questions),
    )
    db.add(quiz_record)
    db.commit()
    db.refresh(quiz_record)

    return quiz_record


def get_progress_analytics(db: Session, user_id: str = "demo-user") -> Dict[str, Any]:
    """
    Computes holistic learning analytics for the student:
    - Summary stats (attempts, questions, accuracy, mastery counts)
    - Topic-wise mastery progression & trends
    - Weak topics & identified misconceptions
    - Adaptive next study recommendations (remediate, explore unquizzed notes, challenge)
    - Timeline of quiz attempts
    """
    # Fetch all attempts for user
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.created_at.asc())
        .all()
    )

    # Fetch stored LearningProgress
    progress_records = (
        db.query(LearningProgress)
        .filter(LearningProgress.user_id == user_id)
        .all()
    )
    progress_by_topic = {p.topic.lower(): p for p in progress_records}

    # Fetch uploaded documents
    uploaded_docs = (
        db.query(StudyDocument)
        .filter(StudyDocument.user_id == user_id)
        .all()
    )

    # Group attempts by topic
    topic_attempts: Dict[str, List[QuizAttempt]] = {}
    for att in attempts:
        t = att.quiz.topic if att.quiz and att.quiz.topic else "General"
        if t not in topic_attempts:
            topic_attempts[t] = []
        topic_attempts[t].append(att)

    # Also include any topics present in progress_records that might not have direct attempts
    for p in progress_records:
        if p.topic not in topic_attempts:
            topic_attempts[p.topic] = []

    # Calculate Topic Mastery
    topic_mastery_list: List[Dict[str, Any]] = []
    weak_topics_list: List[Dict[str, Any]] = []

    total_questions_answered = 0
    total_correct_answers = 0

    for topic_name, att_list in topic_attempts.items():
        prog = progress_by_topic.get(topic_name.lower())

        q_count = sum(a.total_questions for a in att_list)
        corr_count = sum(a.score for a in att_list)

        if prog and prog.total_questions > q_count:
            q_count = prog.total_questions
            corr_count = prog.correct_answers

        mistakes = max(0, q_count - corr_count)
        mastery_score = round((corr_count / q_count) * 100, 1) if q_count > 0 else 0.0

        total_questions_answered += q_count
        total_correct_answers += corr_count

        if mastery_score >= 80.0:
            status = "mastered"
        elif mastery_score >= 50.0:
            status = "in_progress"
        else:
            status = "needs_review"

        # Determine trend
        if len(att_list) <= 1:
            trend = "improving" if mastery_score >= 70.0 else "stable"
        else:
            mid = len(att_list) // 2
            older_avg = sum(a.percentage for a in att_list[:mid]) / max(1, mid)
            newer_avg = sum(a.percentage for a in att_list[mid:]) / max(1, len(att_list) - mid)
            if newer_avg >= older_avg + 5.0:
                trend = "improving"
            elif newer_avg <= older_avg - 5.0:
                trend = "declining"
            else:
                trend = "stable"

        # Extract latest mistake summary & missed concepts
        last_mistake = prog.last_mistake_summary if prog and prog.last_mistake_summary else ""
        missed_concepts = []

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

        if not last_mistake and missed_concepts:
            last_mistake = f"Review: {missed_concepts[0][:60]}..."

        latest_update = (
            att_list[-1].created_at.isoformat()
            if att_list and att_list[-1].created_at
            else (prog.updated_at.isoformat() if prog and prog.updated_at else None)
        )

        item = {
            "topic": topic_name,
            "subtopic": prog.subtopic if prog else None,
            "total_questions": q_count,
            "correct_answers": corr_count,
            "mistake_count": mistakes,
            "mastery_score": mastery_score,
            "status": status,
            "trend": trend,
            "attempts_count": len(att_list),
            "last_mistake_summary": last_mistake or "All questions answered correctly!",
            "updated_at": latest_update,
        }
        topic_mastery_list.append(item)

        if mastery_score < 75.0 or mistakes > 0:
            weak_topics_list.append({
                "topic": topic_name,
                "mastery_score": mastery_score,
                "mistake_count": mistakes,
                "missed_concepts": missed_concepts[:4],
                "recommended_action": f"Take targeted practice to overcome {mistakes} misconception(s) in {topic_name}.",
            })

    topic_mastery_list.sort(key=lambda x: x["mastery_score"], reverse=True)
    weak_topics_list.sort(key=lambda x: (x["mastery_score"], -x["mistake_count"]))

    total_quizzes = len(attempts)
    overall_accuracy = round((total_correct_answers / total_questions_answered) * 100, 1) if total_questions_answered > 0 else 0.0
    mastered_count = sum(1 for t in topic_mastery_list if t["status"] == "mastered")
    weak_count = len(weak_topics_list)

    summary = {
        "total_quizzes_taken": total_quizzes,
        "total_questions_answered": total_questions_answered,
        "total_correct_answers": total_correct_answers,
        "overall_accuracy": overall_accuracy,
        "mastered_topics_count": mastered_count,
        "weak_topics_count": weak_count,
    }

    # Generate Study Recommendations
    recommendations: List[Dict[str, Any]] = []

    # 1. Remediate weak topics
    for wt in weak_topics_list[:2]:
        recommendations.append({
            "type": "remediate",
            "topic": wt["topic"],
            "title": f"🎯 Practice Weak Concepts: {wt['topic']}",
            "reason": f"Current mastery is {wt['mastery_score']}%. You have {wt['mistake_count']} recurring mistakes to fix.",
            "action": "generate_targeted",
            "document_id": None,
        })

    # 2. Explore unquizzed notes
    quizzed_topics_lower = {t.lower() for t in topic_attempts.keys()}
    for doc in uploaded_docs:
        doc_topic = (doc.topic or doc.title).lower()
        if not any(qt in doc_topic or doc_topic in qt for qt in quizzed_topics_lower):
            recommendations.append({
                "type": "explore",
                "topic": doc.topic or doc.title,
                "title": f"📖 Test Knowledge: {doc.title}",
                "reason": "You uploaded these notes but haven't taken a quiz yet.",
                "action": "start_quiz",
                "document_id": doc.id,
            })
            if len(recommendations) >= 4:
                break

    # 3. Challenge mastered topics
    for tm in topic_mastery_list:
        if tm["status"] == "mastered" and len(recommendations) < 4:
            recommendations.append({
                "type": "challenge",
                "topic": tm["topic"],
                "title": f"🏆 Advanced Challenge: {tm['topic']}",
                "reason": f"You've mastered {tm['topic']} at {tm['mastery_score']}%. Test advanced problem scenarios.",
                "action": "start_quiz",
                "document_id": None,
            })

    timeline: List[Dict[str, Any]] = []
    for att in reversed(attempts):
        timeline.append({
            "id": att.id,
            "quiz_id": att.quiz_id,
            "quiz_title": att.quiz.title if att.quiz else "Quiz",
            "quiz_topic": att.quiz.topic if att.quiz else "General",
            "score": att.score,
            "total_questions": att.total_questions,
            "percentage": att.percentage,
            "feedback": att.feedback,
            "created_at": att.created_at.isoformat() if att.created_at else None,
        })

    return {
        "summary": summary,
        "topic_mastery": topic_mastery_list,
        "weak_topics": weak_topics_list,
        "next_recommendations": recommendations,
        "attempts_timeline": timeline,
    }

