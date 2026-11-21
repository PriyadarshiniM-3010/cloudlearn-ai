import io
import logging
import os
import re
import time
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.models import StudyDocument, DocumentChunk, EMBEDDING_DIM
from backend.app.services.gemini_service import (
    get_gemini_api_key,
    call_gemini_robust,
    SYSTEM_INSTRUCTION as BASE_SYSTEM_INSTRUCTION,
    DEFAULT_MODEL,
    MAX_RETRIES,
    INITIAL_BACKOFF_SECONDS,
    GeminiServiceUnavailableError,
    GeminiRateLimitError,
)

logger = logging.getLogger("cloudlearn.rag")

EMBEDDING_MODEL = "gemini-embedding-001"
CHUNK_SIZE = 950  # Characters per chunk (improved semantic window)
CHUNK_OVERLAP = 180  # Overlap between consecutive chunks
MIN_SIMILARITY_THRESHOLD = 0.40  # Minimum cosine similarity to consider context relevant


def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    """Extracts text page-by-page from PDF bytes with enhanced normalization."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_data = []

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        page_text = page.extract_text() or ""
        cleaned = clean_text(page_text)
        if cleaned:
            pages_data.append({"page_number": page_num, "text": cleaned})

    return pages_data


def extract_text_from_txt(file_bytes: bytes) -> List[Dict[str, Any]]:
    """Extracts text from UTF-8 text or markdown file bytes."""
    text_content = file_bytes.decode("utf-8", errors="replace")
    cleaned = clean_text(text_content)
    if not cleaned:
        return []
    return [{"page_number": 1, "text": cleaned}]


def clean_text(text: str) -> str:
    """
    Normalizes whitespace, fixes line wraps, de-hyphenates words across linebreaks,
    and strips unprintable control characters.
    """
    if not text:
        return ""

    # Remove nulls and unprintable characters (preserve newlines, tabs, and unicode characters)
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize carriage returns
    text = re.sub(r"\r\n|\r", "\n", text)
    # Fix hyphenated words broken across line wraps (e.g. "con-\ncurrency" -> "concurrency")
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
    # Normalize common Unicode characters
    text = text.replace("\xa0", " ").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')

    # Reconstruct lines: collapse trailing spaces
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse 3+ newlines to 2 (preserving paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple inline spaces to 1
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def chunk_text(text_content: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Splits text into overlapping chunks, respecting paragraphs, headers,
    and sentence boundaries to preserve semantic coherence.
    """
    if not text_content or len(text_content) <= chunk_size:
        return [text_content] if text_content else []

    paragraphs = text_content.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding paragraph exceeds chunk size, split or push
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = f"{overlap_text}\n\n{para}".strip()
            else:
                # Single paragraph is larger than chunk_size: split by sentences
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                        current_chunk = f"{current_chunk} {sentence}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                            current_chunk = f"{overlap_text} {sentence}".strip()
                        else:
                            # Hard split if single sentence exceeds chunk size
                            for i in range(0, len(sentence), chunk_size - overlap):
                                chunks.append(sentence[i:i + chunk_size])

    if current_chunk and current_chunk not in chunks:
        chunks.append(current_chunk)

    return [c.strip() for c in chunks if len(c.strip()) > 25]


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates 768-dimensional vector embeddings for a list of texts using gemini-embedding-001.
    Handles batching and exponential backoff.
    """
    if not texts:
        return []

    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured in backend/.env.")

    client = genai.Client(api_key=api_key)
    all_embeddings: List[List[float]] = []
    batch_size = 20  # Batch size for embedding calls

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        last_err = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
                )
                batch_vectors = [emb.values for emb in resp.embeddings]
                all_embeddings.extend(batch_vectors)
                last_err = None
                break
            except Exception as e:
                last_err = e
                err_str = str(e)
                if ("503" in err_str or "429" in err_str or "high demand" in err_str.lower()) and attempt < MAX_RETRIES:
                    delay = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                    time.sleep(delay)
                    continue
                break

        if last_err is not None:
            raise RuntimeError(f"Embedding generation failed: {str(last_err)}")

    return all_embeddings


def ingest_document(
    db: Session,
    filename: str,
    file_bytes: bytes,
    user_id: str = "demo-user",
    topic: Optional[str] = None,
    title: Optional[str] = None,
) -> StudyDocument:
    """
    Parses a document (PDF or text), chunks it, generates embeddings,
    and stores metadata and vector chunks in Neon PostgreSQL.
    """
    ext = os.path.splitext(filename)[1].lower()
    doc_title = title.strip() if title and title.strip() else os.path.splitext(filename)[0].replace("_", " ").title()

    if ext == ".pdf":
        pages = extract_text_from_pdf(file_bytes)
    elif ext in [".txt", ".md"]:
        pages = extract_text_from_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Only .pdf, .txt, and .md files are supported.")

    if not pages:
        raise ValueError("Could not extract any readable text from the document. Please ensure it is not an empty or image-only file.")

    # Chunk the pages while tracking page numbers and adding context headers
    prepared_chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    for page_info in pages:
        page_chunks = chunk_text(page_info["text"])
        for chunk_txt in page_chunks:
            # Contextualize chunk with document title and page number
            context_header = f"[{doc_title} | Page {page_info['page_number']}]"
            chunk_with_header = f"{context_header}\n{chunk_txt}"
            prepared_chunks.append({
                "chunk_index": chunk_index,
                "page_number": page_info["page_number"],
                "content": chunk_with_header,
            })
            chunk_index += 1

    if not prepared_chunks:
        raise ValueError("Document contains insufficient text to create study chunks.")

    # Generate embeddings for all chunks (contextual header included)
    chunk_texts = [c["content"] for c in prepared_chunks]
    embeddings = generate_embeddings(chunk_texts)

    # Create document record
    doc = StudyDocument(
        user_id=user_id,
        filename=filename,
        title=doc_title,
        topic=topic,
        file_size_bytes=len(file_bytes),
        page_count=len(pages),
        chunk_count=len(prepared_chunks),
    )
    db.add(doc)
    db.flush()  # Populates doc.id

    # Create chunk records with vector embeddings
    for chunk_meta, emb in zip(prepared_chunks, embeddings):
        chunk_rec = DocumentChunk(
            document_id=doc.id,
            chunk_index=chunk_meta["chunk_index"],
            page_number=chunk_meta["page_number"],
            content=chunk_meta["content"],
            embedding=emb,
        )
        db.add(chunk_rec)

    db.commit()
    db.refresh(doc)
    return doc


def search_relevant_chunks(
    db: Session,
    query: str,
    user_id: str = "demo-user",
    document_id: Optional[int] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Performs cosine similarity vector search on Neon pgvector.
    Returns the top_k most relevant chunks with similarity metrics and document metadata.
    Filters out chunks below MIN_SIMILARITY_THRESHOLD when searching broadly.
    """
    query_embeddings = generate_embeddings([query])
    if not query_embeddings:
        return []

    query_vec = query_embeddings[0]
    vec_literal = "[" + ",".join(str(x) for x in query_vec) + "]"

    # Cosine distance operator <=> in pgvector
    # Similarity = 1.0 - distance
    sql = """
        SELECT
            c.id,
            c.document_id,
            d.title AS document_title,
            d.filename AS document_filename,
            c.page_number,
            c.content,
            (c.embedding <=> :query_vec) AS distance
        FROM document_chunks c
        JOIN study_documents d ON c.document_id = d.id
        WHERE d.user_id = :user_id
    """
    params: Dict[str, Any] = {
        "query_vec": vec_literal,
        "user_id": user_id,
        "limit": top_k * 2 if not document_id else top_k,
    }

    if document_id:
        sql += " AND d.id = :doc_id"
        params["doc_id"] = document_id

    sql += " ORDER BY distance ASC LIMIT :limit"

    rows = db.execute(text(sql), params).fetchall()
    db.commit()

    results = []
    for r in rows:
        dist = float(r.distance) if r.distance is not None else 1.0
        similarity = max(0.0, round(1.0 - dist, 3))

        # Filter out irrelevant chunks below similarity threshold when doing global search
        if not document_id and similarity < MIN_SIMILARITY_THRESHOLD:
            continue

        results.append({
            "chunk_id": r.id,
            "document_id": r.document_id,
            "document_title": r.document_title,
            "document_filename": r.document_filename,
            "page_number": r.page_number,
            "content": r.content,
            "similarity_score": similarity,
            "distance": round(dist, 4),
        })

    # Return top_k results
    return results[:top_k]


def answer_from_notes(
    db: Session,
    question: str,
    user_id: str = "demo-user",
    document_id: Optional[int] = None,
    topic: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Answers a student question grounded in uploaded study notes.
    Combines pgvector similarity retrieval with Gemini 3.8 Flash generation.
    Strictly verifies grounding, cites exact sources, and clearly distinguishes
    information found in notes versus concepts absent from the notes.
    """
    # 1. Retrieve most relevant context chunks
    relevant_chunks = search_relevant_chunks(
        db=db,
        query=question,
        user_id=user_id,
        document_id=document_id,
        top_k=5,
    )

    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured in backend/.env.")

    # Determine if we have strong, relevant context
    has_context = len(relevant_chunks) > 0 and any(
        c["similarity_score"] >= MIN_SIMILARITY_THRESHOLD for c in relevant_chunks
    )

    # 2. Build grounded context block
    if has_context:
        context_blocks = []
        for idx, ch in enumerate(relevant_chunks):
            source_info = f"[Source {idx+1}: {ch['document_title']}"
            if ch.get("page_number"):
                source_info += f", Page {ch['page_number']}"
            source_info += f" | Match: {int(ch['similarity_score'] * 100)}%]"
            context_blocks.append(f"{source_info}\n{ch['content']}")

        context_text = "\n\n---\n\n".join(context_blocks)

        rag_system_prompt = f"""
You are CloudLearn AI, an expert, patient, and precise personalized learning companion.
The student is in "Notes Mode". Your primary role is to answer their question grounded strictly in their uploaded Study Notes Context below.

CRITICAL GROUNDING & CITATION RULES:
1. Base your explanation primarily on the provided STUDY NOTES CONTEXT.
2. CITATION FORMAT: Every key factual claim from the notes MUST cite its exact source in the format: `[Source: Document Title, Page X]` matching the provided headers.
3. STRUCTURE YOUR RESPONSE INTO THESE CLEAR SECTIONS:
   - **### 📖 From Your Uploaded Notes**
     Provide a clear, step-by-step answer based directly on the notes with bold keywords and citations.
   - **### ⚠️ Not Covered in Uploaded Notes (if applicable)**
     If the student's question asks for specific details, tools, or concepts that are NOT present in the provided notes, explicitly state what is missing:
     e.g., "Note: Your uploaded documents do not mention [specific missing topic]."
     Then provide the supplementary explanation under **### 💡 Additional Tutor Context**.
   - **### 🎯 Placement / Exam Takeaways**
     Key definitions, time complexities, or interview questions.
   - **### ❓ Self-Check Question**
     A quick question (with a hint) to test the student's understanding.
"""
    else:
        context_text = "No relevant content was found in the student's uploaded study notes."
        rag_system_prompt = f"""
You are CloudLearn AI, an expert and encouraging personalized learning companion.
The student is asking a question in "Notes Mode", but their uploaded study documents DO NOT cover this topic.

CRITICAL INSTRUCTION FOR MISSING INFORMATION:
1. You MUST begin your response explicitly with:
   `⚠️ **Information Not Found in Uploaded Notes**`
   `Your uploaded study materials do not contain information addressing "{question.strip()}". Below is a clear, comprehensive explanation based on core computer science knowledge:`
2. Then provide the explanation structured with:
   - **### 💡 Core Intuition & Step-by-Step Breakdown**
   - **### 🎯 Exam / Interview Takeaways**
   - **### ❓ Self-Check Question**
"""

    prompt = f"""
STUDY NOTES CONTEXT:
====================
{context_text}
====================

STUDENT QUESTION:
{question.strip()}
"""
    if topic:
        prompt = f"SUBJECT / TOPIC: {topic.strip()}\n{prompt}"

    gen_res = call_gemini_robust(prompt=prompt, system_instruction=rag_system_prompt)

    return {
        "question": question,
        "topic": topic,
        "answer": gen_res["answer"],
        "model": gen_res["model"],
        "has_context": has_context,
        "sources": [
            {
                "document_id": c["document_id"],
                "document_title": c["document_title"],
                "page_number": c["page_number"],
                "excerpt": c["content"][:220] + ("..." if len(c["content"]) > 220 else ""),
                "similarity_score": c["similarity_score"],
            }
            for c in relevant_chunks
        ],
    }
    if topic:
        prompt = f"SUBJECT / TOPIC: {topic.strip()}\n{prompt}"

    gen_res = call_gemini_robust(prompt=prompt, system_instruction=rag_system_prompt)

    return {
        "question": question,
        "topic": topic,
        "answer": gen_res["answer"],
        "model": gen_res["model"],
        "has_context": has_context,
        "sources": [
            {
                "document_id": c["document_id"],
                "document_title": c["document_title"],
                "page_number": c["page_number"],
                "excerpt": c["content"][:200] + ("..." if len(c["content"]) > 200 else ""),
                "similarity_score": c["similarity_score"],
            }
            for c in relevant_chunks
        ],
    }

