import requests
from datetime import datetime, timezone, timedelta

BASE_URL = "http://127.0.0.1:8000"
today = datetime.now(timezone.utc).date()

# Seed DSA problems for demo-user
demo_problems = [
    ("Two Sum", "LeetCode", "Easy", "Arrays", today.strftime("%Y-%m-%d")),
    ("Best Time to Buy and Sell Stock", "LeetCode", "Easy", "Arrays", today.strftime("%Y-%m-%d")),
    ("Valid Anagram", "LeetCode", "Easy", "Strings", today.strftime("%Y-%m-%d")),
    ("Group Anagrams", "LeetCode", "Medium", "Strings", (today - timedelta(days=1)).strftime("%Y-%m-%d")),
    ("Top K Frequent Elements", "LeetCode", "Medium", "Arrays", (today - timedelta(days=1)).strftime("%Y-%m-%d")),
    ("Valid Palindrome", "LeetCode", "Easy", "Strings", (today - timedelta(days=2)).strftime("%Y-%m-%d")),
    ("Container With Most Water", "LeetCode", "Medium", "Two Pointers", (today - timedelta(days=3)).strftime("%Y-%m-%d")),
    ("3Sum", "LeetCode", "Medium", "Two Pointers", (today - timedelta(days=4)).strftime("%Y-%m-%d")),
    ("Binary Search", "LeetCode", "Easy", "Binary Search", (today - timedelta(days=5)).strftime("%Y-%m-%d")),
    ("Invert Binary Tree", "LeetCode", "Easy", "Trees", (today - timedelta(days=6)).strftime("%Y-%m-%d")),
    ("Maximum Depth of Binary Tree", "LeetCode", "Easy", "Trees", (today - timedelta(days=7)).strftime("%Y-%m-%d")),
    ("Climbing Stairs", "LeetCode", "Easy", "Dynamic Programming", (today - timedelta(days=10)).strftime("%Y-%m-%d")),
    ("Coin Change", "LeetCode", "Medium", "Dynamic Programming", (today - timedelta(days=10)).strftime("%Y-%m-%d")),
    ("Longest Increasing Subsequence", "LeetCode", "Medium", "Dynamic Programming", (today - timedelta(days=11)).strftime("%Y-%m-%d")),
    ("Word Break", "LeetCode", "Medium", "Dynamic Programming", (today - timedelta(days=14)).strftime("%Y-%m-%d")),
    ("Course Schedule", "LeetCode", "Medium", "Graphs", (today - timedelta(days=18)).strftime("%Y-%m-%d")),
    ("Number of Islands", "LeetCode", "Medium", "Graphs", (today - timedelta(days=19)).strftime("%Y-%m-%d")),
    ("Trapping Rain Water", "LeetCode", "Hard", "Two Pointers", (today - timedelta(days=25)).strftime("%Y-%m-%d")),
]

print("Seeding demo-user DSA problems...")
for title, plat, diff, top, dt in demo_problems:
    requests.post(f"{BASE_URL}/api/dsa/log", json={
        "user_id": "demo-user",
        "problem_title": title,
        "platform": plat,
        "difficulty": diff,
        "topic": top,
        "activity_date": dt,
        "notes": "Practiced for placement assessment."
    })

# Seed Study Calendar tasks for demo-user
demo_tasks = [
    ("Review OS Paging & Segmentation", "Operating Systems", today.strftime("%Y-%m-%d"), "10:00", "11:30", "high", True),
    ("Solve 3 Graph DFS/BFS Problems", "DSA", today.strftime("%Y-%m-%d"), "14:00", "15:30", "high", False),
    ("Take DBMS Transactions Quiz", "DBMS", today.strftime("%Y-%m-%d"), "16:30", "17:15", "medium", False),
    ("Read LangChain Memory Architecture", "AI & LLMs", (today + timedelta(days=1)).strftime("%Y-%m-%d"), "11:00", "12:00", "medium", False),
    ("Dynamic Programming Practice Sprint", "DSA", (today + timedelta(days=2)).strftime("%Y-%m-%d"), "15:00", "17:00", "high", False),
    ("Mock Technical Interview Revision", "Placement Prep", (today + timedelta(days=4)).strftime("%Y-%m-%d"), "14:00", "16:00", "high", False),
]

print("Seeding demo-user Study Calendar tasks...")
for title, cat, dt, st, et, pri, comp in demo_tasks:
    res = requests.post(f"{BASE_URL}/api/calendar/tasks", json={
        "user_id": "demo-user",
        "title": title,
        "category": cat,
        "task_date": dt,
        "start_time": st,
        "end_time": et,
        "priority": pri,
    })
    if comp and res.status_code == 200:
        t_id = res.json()["id"]
        requests.patch(f"{BASE_URL}/api/calendar/tasks/{t_id}/toggle?user_id=demo-user")

print("Seeding complete!")

