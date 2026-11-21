import sys
import os
import time
import requests
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8000"

def test_new_features():
    print("=" * 70)
    print("CloudLearn AI - Testing New Features: Auth, DSA Heatmap, Study Calendar")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. TEST AUTHENTICATION (SIGNUP, LOGIN, ME)
    # -------------------------------------------------------------
    test_user = f"alex_coder_{int(time.time())}"
    test_email = f"{test_user}@example.com"
    test_pass = "SecurePass123!"

    print(f"\n[Test 1] Testing POST /api/auth/signup for '{test_user}'...")
    res = requests.post(f"{BASE_URL}/api/auth/signup", json={
        "username": test_user,
        "email": test_email,
        "password": test_pass,
        "full_name": "Alex Coder"
    })
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Signup failed: {res.text}"
    signup_data = res.json()
    token = signup_data.get("token")
    user_info = signup_data.get("user")
    print(f"User created: {user_info['username']} ({user_info['email']}) | ID: {user_info['id']}")
    print(f"Token received: {token[:25]}...")

    print("\n[Test 2] Testing POST /api/auth/login...")
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username_or_email": test_user,
        "password": test_pass
    })
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Login failed: {res.text}"
    login_data = res.json()
    assert login_data["user"]["username"] == test_user
    print(f"Login success! Welcome msg: {login_data['message']}")

    print("\n[Test 3] Testing GET /api/auth/me with Bearer token...")
    res = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Auth me failed: {res.text}"
    me_data = res.json()
    print(f"Verified identity: {me_data['username']} (User ID: {me_data['user_id']})")

    # -------------------------------------------------------------
    # 2. TEST DSA HEATMAP & PROBLEM LOG
    # -------------------------------------------------------------
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    print(f"\n[Test 4] Logging DSA problems for '{test_user}' across multiple dates...")
    sample_problems = [
        {"title": "Two Sum", "platform": "LeetCode", "difficulty": "Easy", "topic": "Arrays", "date": today.strftime("%Y-%m-%d")},
        {"title": "Longest Consecutive Sequence", "platform": "LeetCode", "difficulty": "Medium", "topic": "Arrays", "date": today.strftime("%Y-%m-%d")},
        {"title": "Course Schedule II", "platform": "LeetCode", "difficulty": "Medium", "topic": "Graphs", "date": yesterday.strftime("%Y-%m-%d")},
        {"title": "Alien Dictionary", "platform": "LeetCode", "difficulty": "Hard", "topic": "Graphs", "date": yesterday.strftime("%Y-%m-%d")},
        {"title": "Coin Change", "platform": "LeetCode", "difficulty": "Medium", "topic": "Dynamic Programming", "date": two_days_ago.strftime("%Y-%m-%d")},
    ]

    for sp in sample_problems:
        res = requests.post(f"{BASE_URL}/api/dsa/log", json={
            "user_id": test_user,
            "problem_title": sp["title"],
            "platform": sp["platform"],
            "difficulty": sp["difficulty"],
            "topic": sp["topic"],
            "activity_date": sp["date"],
            "notes": "Solved using optimal time complexity."
        })
        assert res.status_code == 200, f"Logging problem failed: {res.text}"
        data = res.json()
        print(f"  + Logged: [{data['difficulty']}] {data['problem_title']} ({data['topic']}) on {data['activity_date']}")

    print("\n[Test 5] Testing GET /api/dsa/heatmap...")
    res = requests.get(f"{BASE_URL}/api/dsa/heatmap?user_id={test_user}")
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Heatmap failed: {res.text}"
    hm_data = res.json()
    print(f"Total Problems Solved: {hm_data['total_problems']}")
    print(f"Current Streak: {hm_data['current_streak']} day(s)")
    print(f"Max Streak: {hm_data['max_streak']} day(s)")
    print(f"Active Days Count: {hm_data['active_days_count']}")
    print(f"Difficulty Breakdown: {hm_data['difficulty_breakdown']}")
    print(f"Platform Breakdown: {hm_data['platform_breakdown']}")
    print(f"Topic Breakdown: {hm_data['topic_breakdown']}")
    print(f"Total Heatmap Days: {len(hm_data['heatmap_days'])}")

    # -------------------------------------------------------------
    # 3. TEST STUDY CALENDAR (CREATE, GET, TOGGLE, UPDATE, DELETE)
    # -------------------------------------------------------------
    print(f"\n[Test 6] Testing POST /api/calendar/tasks for '{test_user}'...")
    res = requests.post(f"{BASE_URL}/api/calendar/tasks", json={
        "user_id": test_user,
        "title": "OS Paging & Virtual Memory Revision",
        "description": "Review page replacement algorithms (LRU, FIFO) from lecture notes.",
        "category": "Operating Systems",
        "task_date": today.strftime("%Y-%m-%d"),
        "start_time": "14:00",
        "end_time": "15:30",
        "priority": "high"
    })
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Create task failed: {res.text}"
    task1 = res.json()
    print(f"Task 1 created: [{task1['id']}] {task1['title']} ({task1['category']}) at {task1['start_time']} - Completed: {task1['is_completed']}")

    # Create second task
    res2 = requests.post(f"{BASE_URL}/api/calendar/tasks", json={
        "user_id": test_user,
        "title": "DSA Mock Interview Prep: Graph Traversal",
        "category": "DSA",
        "task_date": today.strftime("%Y-%m-%d"),
        "start_time": "17:00",
        "end_time": "18:00",
        "priority": "medium"
    })
    task2 = res2.json()
    print(f"Task 2 created: [{task2['id']}] {task2['title']}")

    print("\n[Test 7] Testing PATCH /api/calendar/tasks/{id}/toggle...")
    res = requests.patch(f"{BASE_URL}/api/calendar/tasks/{task1['id']}/toggle?user_id={test_user}")
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Toggle task failed: {res.text}"
    toggled = res.json()
    print(f"Toggled Task 1 completion: is_completed = {toggled['is_completed']}")
    assert toggled["is_completed"] is True

    print("\n[Test 8] Testing GET /api/calendar/tasks...")
    month_prefix = today.strftime("%Y-%m")
    res = requests.get(f"{BASE_URL}/api/calendar/tasks?user_id={test_user}&month={month_prefix}")
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Get tasks failed: {res.text}"
    cal_data = res.json()
    tasks = cal_data["tasks"]
    summary = cal_data["summary"]
    print(f"Fetched {len(tasks)} task(s) for month {month_prefix}:")
    for t in tasks:
        print(f"  - [{t['id']}] {'[DONE]' if t['is_completed'] else '[TODO]'} {t['title']} ({t['category']}) - {t['task_date']} {t['start_time'] or ''}")
    print(f"Month Summary: Total: {summary['total_tasks']} | Done: {summary['completed_tasks']} | Rate: {summary['completion_rate']}%")

    print("\n" + "=" * 70)
    print("ALL NEW BACKEND API TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_new_features()

