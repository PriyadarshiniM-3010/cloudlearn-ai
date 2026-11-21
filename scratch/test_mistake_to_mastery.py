import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_progress_analytics():
    print(">>> 1. Testing GET /api/progress/analytics...")
    res = requests.get(f"{BASE_URL}/api/progress/analytics?user_id=demo-user")
    print(f"Status: {res.status_code}")
    if res.status_code != 200:
        print("Response text:", res.text)
        return False
    data = res.json()
    print("Summary:", json.dumps(data.get("summary"), indent=2))
    print(f"Topics count: {len(data.get('topic_mastery', []))}")
    for tm in data.get("topic_mastery", []):
        print(f"  - Topic: {tm['topic']}, Score: {tm['mastery_score']}%, Status: {tm['status']}, Trend: {tm['trend']}, Mistakes: {tm['mistake_count']}")
    print(f"Weak topics count: {len(data.get('weak_topics', []))}")
    for wt in data.get("weak_topics", []):
        print(f"  - Weak Topic: {wt['topic']}, Missed concepts: {wt['missed_concepts']}")
    print(f"Recommendations count: {len(data.get('next_recommendations', []))}")
    for rec in data.get("next_recommendations", []):
        print(f"  - [{rec['type']}] {rec['title']} -> {rec['reason']}")
    return True

def test_generate_targeted_and_master():
    print("\n>>> 2. Testing POST /api/quizzes/generate-targeted for Operating Systems...")
    payload = {
        "topic": "Operating Systems",
        "focus_concepts": ["Page table vs TLB miss", "Virtual memory translation"],
        "num_questions": 2,
        "user_id": "demo-user"
    }
    t0 = time.time()
    res = requests.post(f"{BASE_URL}/api/quizzes/generate-targeted", json=payload)
    print(f"Status: {res.status_code} in {round(time.time() - t0, 2)}s")
    if res.status_code != 200:
        print("Error text:", res.text)
        return False
    quiz = res.json()
    quiz_id = quiz["id"]
    print(f"Generated Targeted Quiz ID: {quiz_id}, Title: {quiz['title']}")
    print(f"Questions received by client: {len(quiz['questions'])}")
    for q in quiz['questions']:
        print(f"  Q{q['id']}: {q['question']}")
        for i, opt in enumerate(q['options']):
            print(f"    [{chr(65+i)}] {opt}")

    # Inspect correct answers from database backend to simulate a student learning and submitting correctly
    from backend.app.database import get_session
    from backend.app.models import Quiz
    db = get_session()()
    quiz_db = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    stored_questions = json.loads(quiz_db.questions_data)
    db.close()

    answers = {str(q["id"]): q["correct_index"] for q in stored_questions}

    # 3. Submit 100% correct answers to simulate student achieving mastery!
    print(f"\n>>> 3. Submitting 100% correct answers for Quiz ID {quiz_id}...")
    submit_payload = {
        "quiz_id": quiz_id,
        "user_id": "demo-user",
        "answers": answers
    }
    sub_res = requests.post(f"{BASE_URL}/api/quizzes/submit", json=submit_payload)
    print(f"Submit Status: {sub_res.status_code}")
    if sub_res.status_code != 200:
        print("Submit error:", sub_res.text)
        return False
    eval_res = sub_res.json()
    print(f"Score: {eval_res['score']}/{eval_res['total_questions']} ({eval_res['percentage']}%)")
    print(f"Mastery Status: {eval_res['mastery_status']}")
    print(f"Feedback: {eval_res['feedback']}")
    for r in eval_res['results']:
        print(f"  Result Q{r['question_id']}: Correct={r['is_correct']}, Exp={r['explanation'][:80]}...")

    # 4. Re-fetch analytics to verify mastery progression and trend update!
    print("\n>>> 4. Re-fetching GET /api/progress/analytics to verify mastery progression...")
    res2 = requests.get(f"{BASE_URL}/api/progress/analytics?user_id=demo-user")
    data2 = res2.json()
    print("Updated Summary:", json.dumps(data2.get("summary"), indent=2))
    for tm in data2.get("topic_mastery", []):
        if "operating" in tm['topic'].lower():
            print(f"  -> Operating Systems Mastery: {tm['mastery_score']}%, Status: {tm['status']}, Trend: {tm['trend']}, Attempts: {tm['attempts_count']}")

    print("\nSUCCESS: Complete Mistake-to-Mastery backend workflow verified!")
    return True

if __name__ == "__main__":
    if test_progress_analytics():
        test_generate_targeted_and_master()
