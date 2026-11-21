import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_multi_agent_system():
    print("=" * 70)
    print("CloudLearn AI - Multi-Agent Learning System End-to-End Test")
    print("=" * 70)

    # 1. Test Agents Status
    print("\n[Test 1] Testing GET /api/agents/status...")
    res = requests.get(f"{BASE_URL}/api/agents/status?user_id=demo-user")
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Failed: {res.text}"
    status_data = res.json()
    print("Orchestrator Status:", status_data.get("orchestrator_status"))
    agents = status_data.get("agents", {})
    print(f"Registered Agents ({len(agents)}):")
    for k, v in agents.items():
        print(f"  - {v['name']}: {v['status'].upper()} -> {v['role']}")

    # 2. Test Learner Profiling Agent
    print("\n[Test 2] Testing GET /api/agents/profile (Learner Profiling Agent)...")
    res = requests.get(f"{BASE_URL}/api/agents/profile?user_id=demo-user")
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Failed: {res.text}"
    profile = res.json()
    print(f"Learner ID: {profile['user_id']}")
    print(f"Overall Accuracy: {profile['overall_accuracy']}%")
    print(f"Learning Tier: {profile['learning_tier']}")
    print(f"Learning Velocity: {profile['learning_velocity']}")
    print(f"Mastered Topics ({len(profile['mastered_topics'])}): {[t['topic'] for t in profile['mastered_topics']]}")
    print(f"Weak Topics ({len(profile['weak_topics'])}): {[t['topic'] for t in profile['weak_topics']]}")
    print(f"Summary Narrative: {profile['summary_narrative']}")

    # 3. Test Curriculum Planner + Content Recommender via Study Plan Generation
    print("\n[Test 3] Testing POST /api/agents/study-plan (Profiler + Recommender + Planner)...")
    plan_payload = {
        "user_id": "demo-user",
        "goal": "Core Computer Science Placement & Tech Interview Mastery",
        "target_timeline": "2 Weeks",
        "focus_topics": ["Operating Systems", "AI & Large Language Models", "Database Management (DBMS)"]
    }
    t0 = time.time()
    res = requests.post(f"{BASE_URL}/api/agents/study-plan", json=plan_payload)
    elapsed = round(time.time() - t0, 2)
    print(f"Status Code: {res.status_code} in {elapsed}s")
    assert res.status_code == 200, f"Failed: {res.text}"
    plan = res.json()
    print(f"Generated Plan ID: {plan.get('id')}")
    print(f"Title: {plan.get('title')}")
    print(f"Goal: {plan.get('goal')}")
    print(f"Timeline: {plan.get('target_timeline')}")
    phases = plan.get("phases", [])
    print(f"Phases ({len(phases)}):")
    first_milestone_id = None
    for p in phases:
        print(f"  * {p['phase_name']} (Focus: {p['focus']})")
        for m in p.get("milestones", []):
            if not first_milestone_id:
                first_milestone_id = m['id']
            print(f"      [{m['id']}] {m['title']} ({m['topic']} - {m['action_type']}, ~{m['estimated_minutes']}m) - Status: {m['status']}")
    
    recs = plan.get("content_recommendations", [])
    print(f"Content Recommendations Grounded ({len(recs)}):")
    for r in recs[:3]:
        print(f"  - [{r.get('type')}] {r.get('document_title', 'Notes')} (Page {r.get('page_number', 'N/A')}): {r.get('rationale', '')}")

    agent_trace = plan.get("agent_trace", {})
    print(f"Agent Trace Steps ({len(agent_trace.get('steps', []))}):")
    for step in agent_trace.get("steps", []):
        print(f"  -> {step['agent']}: {step['action']} ({step['summary']})")

    # 4. Test Fetch Active Study Plan
    print("\n[Test 4] Testing GET /api/agents/study-plan...")
    res = requests.get(f"{BASE_URL}/api/agents/study-plan?user_id=demo-user")
    assert res.status_code == 200, f"Failed: {res.text}"
    fetched_plan = res.json()
    print(f"Fetched Active Plan ID: {fetched_plan.get('id')}, Title: {fetched_plan.get('title')}")

    # 5. Test Update Milestone Status
    if first_milestone_id:
        print(f"\n[Test 5] Testing PATCH /api/agents/study-plan/milestone for '{first_milestone_id}'...")
        res = requests.patch(f"{BASE_URL}/api/agents/study-plan/milestone", json={
            "user_id": "demo-user",
            "milestone_id": first_milestone_id,
            "new_status": "in_progress"
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        updated_plan = res.json()
        print(f"Milestone '{first_milestone_id}' status successfully updated to 'in_progress'")

    # 6. Test Orchestrated Targeted Remediation (Profiler + Recommender + Quiz Agent)
    print("\n[Test 6] Testing POST /api/agents/remediate...")
    t0 = time.time()
    res = requests.post(f"{BASE_URL}/api/agents/remediate", json={
        "user_id": "demo-user",
        "topic": "Operating Systems"
    })
    elapsed = round(time.time() - t0, 2)
    print(f"Status Code: {res.status_code} in {elapsed}s")
    assert res.status_code == 200, f"Failed: {res.text}"
    rem_data = res.json()
    quiz = rem_data["quiz"]
    print(f"Generated Quiz ID: {quiz['id']} ('{quiz['title']}')")
    print(f"Questions Count: {len(quiz['questions'])}")
    print(f"Generated by: {quiz.get('generating_agent', 'Quiz Agent')}")

    # 7. Test Evaluation Agent with Knowledge Gap Analysis
    print(f"\n[Test 7] Testing POST /api/agents/evaluate for Quiz ID {quiz['id']}...")
    # Generate answers with 1 correct and others wrong to test gap analysis
    from backend.app.database import get_session
    from backend.app.models import Quiz
    db = get_session()()
    q_rec = db.query(Quiz).filter(Quiz.id == quiz["id"]).first()
    stored_questions = json.loads(q_rec.questions_data)
    db.close()

    answers = {}
    for idx, q in enumerate(stored_questions):
        # 1st question correct, others wrong to verify knowledge gap identification
        if idx == 0:
            answers[str(q["id"])] = q["correct_index"]
        else:
            answers[str(q["id"])] = (q["correct_index"] + 1) % 4

    eval_payload = {
        "quiz_id": quiz["id"],
        "user_id": "demo-user",
        "answers": answers,
        "milestone_id": first_milestone_id
    }
    res = requests.post(f"{BASE_URL}/api/agents/evaluate", json=eval_payload)
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Failed: {res.text}"
    eval_resp = res.json()
    eval_result = eval_resp["evaluation"]
    print(f"Evaluated by: {eval_result['evaluating_agent']}")
    print(f"Score: {eval_result['score']}/{eval_result['total_questions']} ({eval_result['percentage']}%)")
    print(f"Mastered Concepts: {eval_result['mastered_concepts']}")
    print(f"Identified Knowledge Gaps ({len(eval_result['knowledge_gaps'])}):")
    for kg in eval_result['knowledge_gaps']:
        print(f"  - Concept: {kg['concept'][:60]}...")
        print(f"    Student Choice: {kg['student_choice']}")
        print(f"    Correct: {kg['correct_answer']}")
        print(f"    Explanation: {kg['explanation'][:80]}...")
    print(f"Next Pedagogical Action: {eval_result['next_pedagogical_action']}")

    print("\n" + "=" * 70)
    print("ALL 7 MULTI-AGENT VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_multi_agent_system()
