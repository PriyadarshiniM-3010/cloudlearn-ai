import sys
import os
import json
import time

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure backend package can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_full_pipeline():
    print("==================================================")
    print("CloudLearn AI - Complete Pipeline Verification")
    print("==================================================")

    # 1. Health Check
    print("\n[Step 1] Checking backend health...")
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code} {r.text}"
    health = r.json()
    print(f"[PASS] Backend healthy: status='{health.get('status')}', database='{health.get('database')}', gemini='{health.get('gemini_model')}'")

    # 2. Auth: User Signup
    ts = int(time.time())
    new_username = f"learner_{ts}"
    new_email = f"learner_{ts}@cloudlearn.ai"
    password = "SuperSecretPassword123!"

    print(f"\n[Step 2] Testing User Signup for '{new_username}'...")
    signup_payload = {
        "username": new_username,
        "email": new_email,
        "password": password,
        "full_name": "Test Learner Alpha"
    }
    r = client.post("/api/auth/signup", json=signup_payload)
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    auth_data = r.json()
    user_id = auth_data["user"]["user_id"]
    token = auth_data["access_token"]
    assert token, "Token missing in signup response"
    print(f"[PASS] Signup successful: user_id='{user_id}', username='{auth_data['user']['username']}'")

    # 3. Auth: Verify /api/auth/me with Bearer token
    print("\n[Step 3] Testing /api/auth/me with Bearer token...")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200, f"Auth me failed: {r.status_code} {r.text}"
    me = r.json()
    assert me["username"] == new_username
    print(f"[PASS] /api/auth/me verified: Authenticated as '{me['username']}' ({me['email']})")

    # 4. Auth: User Login
    print(f"\n[Step 4] Testing User Login with credentials...")
    login_payload = {
        "username": new_username,
        "password": password
    }
    r = client.post("/api/auth/login", json=login_payload)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    login_data = r.json()
    assert login_data["access_token"], "Token missing in login response"
    print(f"[PASS] Login verified: Welcome back '{login_data['user']['full_name']}'")

    # 5. DSA Heatmap: Log Problems for new user
    print(f"\n[Step 5] Testing DSA Problem Logging & Streak Calculation...")
    problems = [
        {"title": "Two Sum", "platform": "LeetCode", "difficulty": "Easy", "topic": "Arrays", "date": "2026-11-01"},
        {"title": "Add Two Numbers", "platform": "LeetCode", "difficulty": "Medium", "topic": "Linked Lists", "date": "2026-11-01"},
        {"title": "LRU Cache", "platform": "LeetCode", "difficulty": "Medium", "topic": "Design", "date": "2026-11-02"},
        {"title": "Trapping Rain Water", "platform": "LeetCode", "difficulty": "Hard", "topic": "Two Pointers", "date": "2026-11-02"},
    ]
    for p in problems:
        dsa_req = {
            "user_id": user_id,
            "problem_title": p["title"],
            "platform": p["platform"],
            "difficulty": p["difficulty"],
            "topic": p["topic"],
            "activity_date": p["date"],
            "notes": f"Practiced {p['topic']} logic."
        }
        r = client.post("/api/dsa/log", json=dsa_req)
        assert r.status_code == 200, f"Failed to log problem {p['title']}: {r.status_code} {r.text}"
    print(f"[PASS] Logged {len(problems)} DSA problems for user '{user_id}'")

    # 6. DSA Heatmap: Fetch & verify heatmap grid
    print(f"\n[Step 6] Fetching DSA Heatmap for '{user_id}'...")
    r = client.get(f"/api/dsa/heatmap?user_id={user_id}")
    assert r.status_code == 200, f"Failed to get heatmap: {r.status_code} {r.text}"
    heatmap = r.json()
    assert heatmap["total_problems"] == 4, f"Expected 4 problems, got {heatmap['total_problems']}"
    assert heatmap["active_days_count"] == 2, f"Expected 2 active days, got {heatmap['active_days_count']}"
    assert len(heatmap["days"]) == 365, f"Expected 365 days, got {len(heatmap['days'])}"
    assert heatmap["difficulty_breakdown"]["Easy"] == 1
    assert heatmap["difficulty_breakdown"]["Medium"] == 2
    assert heatmap["difficulty_breakdown"]["Hard"] == 1
    print(f"[PASS] Heatmap data verified: total={heatmap['total_problems']}, active_days={heatmap['active_days_count']}, current_streak={heatmap['current_streak']}, max_streak={heatmap['max_streak']}")

    # 7. User Data Isolation: Check demo-user vs new user
    print(f"\n[Step 7] Verifying User Data Isolation (demo-user vs {user_id})...")
    r_demo = client.get("/api/dsa/heatmap?user_id=demo-user")
    assert r_demo.status_code == 200
    demo_heatmap = r_demo.json()
    assert demo_heatmap["total_problems"] != heatmap["total_problems"], "Data isolation failure: demo-user and new user have identical problem count!"
    print(f"[PASS] User Isolation Confirmed: new user has {heatmap['total_problems']} problems, demo-user has {demo_heatmap['total_problems']} problems.")

    # 8. Study Calendar: Create, Toggle, and Summarize Tasks
    print(f"\n[Step 8] Testing Study Calendar task management...")
    current_month = "2026-11"
    task_req = {
        "user_id": user_id,
        "title": "Master Coffman Deadlock Conditions",
        "category": "Core CS",
        "task_date": "2026-11-05",
        "start_time": "15:00",
        "end_time": "16:30",
        "priority": "high",
        "description": "Review OS notes on Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait."
    }
    r = client.post("/api/calendar/tasks", json=task_req)
    assert r.status_code == 200, f"Failed to create task: {r.status_code} {r.text}"
    created_task = r.json()
    task_id = created_task["id"]
    assert created_task["is_completed"] is False
    print(f"[PASS] Scheduled study task: id={task_id}, title='{created_task['title']}'")

    # Toggle task to completed
    r = client.patch(f"/api/calendar/tasks/{task_id}/toggle?user_id={user_id}")
    assert r.status_code == 200
    toggled = r.json()
    assert toggled["is_completed"] is True
    print(f"[PASS] Toggled task completion: is_completed={toggled['is_completed']}")

    # Verify Calendar Summary for month
    r = client.get(f"/api/calendar/tasks?user_id={user_id}&month={current_month}")
    assert r.status_code == 200
    cal_data = r.json()
    summary = cal_data["summary"]
    assert summary["total_tasks"] == 1
    assert summary["completed_tasks"] == 1
    assert summary["completion_rate"] == 100.0
    print(f"[PASS] Month summary verified: total={summary['total_tasks']}, completed={summary['completed_tasks']}, rate={summary['completion_rate']}%")

    # 9. Existing Features Regression: Multi-Agent Status
    print(f"\n[Step 9] Regression Test: Checking Multi-Agent Orchestrator Status...")
    r = client.get(f"/api/agents/status?user_id={user_id}")
    assert r.status_code == 200, f"Agent status failed: {r.status_code} {r.text}"
    agents_status = r.json()
    assert agents_status["orchestrator_status"] in ("operational", "active")
    assert len(agents_status["agents"]) == 5
    print(f"[PASS] Multi-Agent Orchestrator confirmed {agents_status['orchestrator_status']} with all 5 agents: {list(agents_status['agents'].keys())}")

    # 10. Existing Features Regression: RAG & Notes QA
    print(f"\n[Step 10] Regression Test: Checking Notes & Document Listing...")
    r = client.get("/api/documents?user_id=demo-user")
    assert r.status_code == 200
    docs = r.json()
    print(f"[PASS] Retrieved {len(docs)} documents in Neon pgvector store for demo-user.")

    print("\n==================================================")
    print("ALL 10 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    test_full_pipeline()
