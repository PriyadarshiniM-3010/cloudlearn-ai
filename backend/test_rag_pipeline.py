import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import get_session
from backend.app.services.rag_service import (
    ingest_document,
    search_relevant_chunks,
    answer_from_notes,
)

sample_notes = """CloudLearn Operating Systems Lecture Notes
Chapter: Paging and Virtual Memory Architecture

In modern computer architectures, Virtual Memory provides an illusion to applications that each has a contiguous block of dedicated RAM.
Physical memory is divided into fixed-size units called frames (typically 4KB in size).
The process logical memory is partitioned into units of the exact same size called pages.

When an application references a memory address, the Memory Management Unit (MMU) uses the Page Table to translate virtual addresses into physical frame numbers.

If a referenced page is marked invalid (not currently loaded into physical RAM), the MMU raises a Page Fault hardware interrupt.
The Operating System's page fault handler:
1. Identifies the faulting virtual address.
2. Locates the required page on the secondary storage backing store.
3. Finds a free frame in physical RAM (or invokes a Page Replacement Algorithm like LRU or FIFO if RAM is full).
4. Issues an I/O request to load the page into the selected frame.
5. Updates the Page Table and sets the valid/invalid bit to valid.
6. Restarts the CPU instruction that triggered the fault."""

Session = get_session()
db = Session()
try:
    print("1. Ingesting test study document into Neon pgvector...")
    doc = ingest_document(
        db=db,
        filename="os_paging_notes.md",
        file_bytes=sample_notes.encode("utf-8"),
        user_id="demo-user",
        topic="Operating Systems",
        title="OS Paging & Virtual Memory",
    )
    print(f"Document ingested! ID: {doc.id}, Title: {doc.title}, Chunks: {doc.chunk_count}")

    print("\n2. Testing vector similarity search on Neon pgvector...")
    query = "What is the role of the MMU and what happens during a page fault?"
    chunks = search_relevant_chunks(db=db, query=query, user_id="demo-user", top_k=2)
    print(f"Found {len(chunks)} relevant chunks:")
    for c in chunks:
        print(f" - Doc: '{c['document_title']}' | Score: {c['similarity_score']} | Excerpt: {c['content'][:120]}...")

    print("\n3. Testing grounded question answering with Gemini 3.8 Flash...")
    answer_res = answer_from_notes(db=db, question=query, user_id="demo-user")
    print("Model:", answer_res["model"])
    print("Has Context:", answer_res["has_context"])
    print("Sources:", [s["document_title"] for s in answer_res["sources"]])
    print("\n--- ANSWER PREVIEW ---")
    print(answer_res["answer"][:500])

finally:
    db.close()
