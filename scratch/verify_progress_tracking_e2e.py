import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def run_e2e_verification():
    print("=" * 70)
    print("CloudLearn AI - Progress Tracking & Mistake-to-Mastery Verification")
    print("=" * 70)

    # 1. Health check
    print("\n[Step 1] Verifying System Health & Database Connection...")
    h_res = requests.get(f"{BASE_URL}/health")
    assert h_res.status_code == 200, f"Health check failed: {h_res.status_code}"
    h_data = h_res.json()
    print("  FastAPI Status:", h_data.get("status"))
    print("  Neon PostgreSQL:", h_data.get("database", {}).get("message"))
    print("  Gemini Model:", h_data.get("gemini", {}).get("model"))
    print(f"  Indexed Docs: {h_data.get('rag', {}).get('documents_count')}, Chunks: {h_data.get('rag', {}).get('chunks_count')}")

    # 2. Get Progress Analytics
    print("\n[Step 2] Fetching Student Progress Analytics...")
    a_res = requests.get(f"{BASE_URL}/api/progress/analytics?user_id=demo-user")
    assert a_res.status_code == 200, f"Analytics fetch failed: {a_res.status_code}"
    a_data = a_res.json()
    
    summary = a_data.get("summary", {})
    print(f"  Total Quizzes Taken: {summary.get('total_quizzes_taken')}")
    print(f"  Total Questions: {summary.get('total_questions_answered')} (Correct: {summary.get('total_correct_answers')})")
    print(f"  Overall Accuracy: {summary.get('overall_accuracy')}%")
    print(f"  Mastered Topics: {summary.get('mastered_topics_count')}")
    print(f"  Weak Topics: {summary.get('weak_topics_count')}")

    # Topic Mastery & Trends
    print("\n  Topic Mastery & Trends:")
    for tm in a_data.get("topic_mastery", []):
        print(f"    * {tm['topic']}: {tm['mastery_score']}% ({tm['correct_answers']}/{tm['total_questions']}) | Status: {tm['status'].upper()} | Trend: {tm['trend'].upper()} ({tm['attempts_count']} attempts)")

    # Weak Topics & Misconceptions
    weak_topics = a_data.get("weak_topics", [])
    print(f"\n  Identified Weak Topics ({len(weak_topics)}):")
    for wt in weak_topics:
        print(f"    * Topic: {wt['topic']} (Score: {wt['mastery_score']}%, Mistakes: {wt['mistake_count']})")
        print(f"      Missed concepts: {len(wt.get('missed_concepts', []))} items")
        for mc in wt.get("missed_concepts", [])[:2]:
            print(f"        - {mc[:75]}...")

    # Recommendations
    recs = a_data.get("next_recommendations", [])
    print(f"\n  Adaptive AI Recommendations ({len(recs)}):")
    for r in recs:
        print(f"    * [{r['type'].upper()}] {r['title']}")
        print(f"      Reason: {r['reason']}")

    # 3. Generate Targeted Remediation Quiz on a Weak Topic
    target_topic = weak_topics[0]["topic"] if weak_topics else "AI & Large Language Models"
    target_concepts = weak_topics[0].get("missed_concepts", [])[:2] if weak_topics else ["LangChain vector retrieval", "LangChain agent tools"]
    
    print(f"\n[Step 3] Generating Targeted Remediation Quiz for '{target_topic}'...")
    print(f"  Targeted Concepts: {target_concepts}")
    t0 = time.time()
    tq_res = requests.post(f"{BASE_URL}/api/quizzes/generate-targeted", json={
        "topic": target_topic,
        "focus_concepts": target_concepts,
        "num_questions": 2,
        "user_id": "demo-user"
    })
    elapsed = round(time.time() - t0, 2)
    assert tq_res.status_code == 200, f"Targeted quiz generation failed: {tq_res.text}"
    tq_data = tq_res.json()
    quiz_id = tq_data["id"]
    print(f"  Generated Quiz ID {quiz_id} in {elapsed}s: '{tq_data['title']}'")
    print(f"  Questions Received: {len(tq_data['questions'])}")
    for q in tq_data["questions"]:
        print(f"    Q{q['id']}: {q['question']}")
        for i, opt in enumerate(q['options']):
            print(f"      [{chr(65+i)}] {opt}")

    # 4. Submit Answers and Evaluate
    print(f"\n[Step 4] Submitting Targeted Quiz (ID: {quiz_id})...")
    # Load correct answers from database backend
    from backend.app.database import get_session
    from backend.app.models import Quiz
    db = get_session()()
    quiz_record = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    stored_questions = json.loads(quiz_record.questions_data)
    db.close()

    answers = {str(q["id"]): q["correct_index"] for q in stored_questions}
    sub_res = requests.post(f"{BASE_URL}/api/quizzes/submit", json={
        "quiz_id": quiz_id,
        "user_id": "demo-user",
        "answers": answers
    })
    assert sub_res.status_code == 200, f"Submit failed: {sub_res.text}"
    eval_res = sub_res.json()
    print(f"  Score: {eval_res['score']}/{eval_res['total_questions']} ({eval_res['percentage']}%)")
    print(f"  Mastery Status: {eval_res['mastery_status']}")
    print(f"  Feedback: {eval_res['feedback']}")

    # 5. Verify Progression in Analytics
    print("\n[Step 5] Verifying Updated Progress Analytics in Neon PostgreSQL...")
    a_res2 = requests.get(f"{BASE_URL}/api/progress/analytics?user_id=demo-user")
    assert a_res2.status_code == 200
    a_data2 = a_res2.json()
    new_summary = a_data2.get("summary", {})
    print(f"  Updated Total Quizzes: {new_summary.get('total_quizzes_taken')}")
    print(f"  Updated Questions Answered: {new_summary.get('total_questions_answered')}")
    print(f"  Updated Overall Accuracy: {new_summary.get('overall_accuracy')}%")

    for tm in a_data2.get("topic_mastery", []):
        if target_topic.lower() in tm['topic'].lower():
            print(f"  Progression for {tm['topic']}:")
            print(f"    Mastery Score: {tm['mastery_score']}%")
            print(f"    Status: {tm['status']}")
            print(f"    Trend: {tm['trend']}")
            print(f"    Attempts: {tm['attempts_count']}")

    print("\n" + "=" * 70)
    print("ALL VERIFICATIONS PASSED: Mistake-to-Mastery Pipeline Fully Operational!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_verification()

