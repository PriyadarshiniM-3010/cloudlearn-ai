# 🎓 CloudLearn AI — Multi-Agent Personalized Learning Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![Neon](https://img.shields.io/badge/Neon-PostgreSQL%20%2B%20pgvector-00E599.svg?style=flat&logo=postgresql&logoColor=white)](https://neon.tech)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-3.8%20Flash-4285F4.svg?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**CloudLearn AI** is an intelligent, agentic learning platform designed to help students master complex computer science concepts, track mistakes, schedule study tasks, and prepare for technical placements. It integrates **Google Gemini 3.8 Flash**, **Neon Cloud Serverless PostgreSQL with pgvector**, a **5-Agent Autonomous Learning System**, a **LeetCode-style DSA activity heatmap**, and an **interactive study calendar**.

---

## 📑 Table of Contents

- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Multi-Agent Learning Architecture](#-multi-agent-learning-architecture)
- [Database Schema (Neon PostgreSQL)](#-database-schema-neon-postgresql)
- [Tech Stack](#-tech-stack)
- [API Reference](#-api-reference)
- [Local Installation & Setup](#-local-installation--setup)
- [Environment Variables](#-environment-variables)
- [Verification & Automated Tests](#-verification--automated-tests)

---

## 🏗️ System Architecture

```text
                               ┌────────────────────────────────────────────────────────┐
                               │             React + Vite Frontend (SPA)                │
                               │               http://localhost:5173                    │
                               └──────────────────────────┬─────────────────────────────┘
                                                          │ HTTP / JSON / Form-Data
                                                          ▼
                               ┌────────────────────────────────────────────────────────┐
                               │                 FastAPI REST Backend                   │
                               │                http://localhost:8000                   │
                               └────────────┬─────────────┬─────────────┬───────────────┘
                                            │             │             │
                    ┌───────────────────────┘             │             └───────────────────────┐
                    ▼                                     ▼                                     ▼
     ┌────────────────────────────┐        ┌────────────────────────────┐        ┌────────────────────────────┐
     │      Google Gemini API     │        │    Central Orchestrator    │        │       Neon PostgreSQL      │
     │  - gemini-3.8-flash        │        │   (5 Autonomous Agents)    │        │   - Users & Auth           │
     │  - text-embedding-004      │        │  - Profiler    - Planner   │        │   - pgvector Embeddings    │
     │  - Exponential Retries     │        │  - Recommender - Quiz      │        │   - DSA Activity Tracker   │
     │    (503 / 429 Handling)    │        │  - Evaluator               │        │   - Study Calendar Tasks   │
     └────────────────────────────┘        └────────────────────────────┘        └────────────────────────────┘
```

---

## 🌟 Key Features

### 1. 🏠 Executive Command Center Dashboard
- **Unified Overview**: Real-time snapshot of notes indexed, quiz accuracy %, LeetCode streaks, and calendar task completion.
- **Today's Schedule Widget**: View and check off scheduled tasks directly from the home dashboard.
- **Adaptive AI Focus**: Live insights from the Multi-Agent System highlighting primary weak topics or active milestone objectives.
- **Mini-DSA Activity Strip**: 14-day quick glance of problem-solving consistency.
- **Recent Activity Feed**: Chronological stream of recent quiz attempts and solved algorithm problems.
- **1-Click Launchpad**: Instant navigation to any study tool.

### 2. 📚 Study Notes RAG Knowledge Base
- **Multi-Format Ingestion**: Upload `.pdf`, `.txt`, and `.md` lecture notes and cheatsheets.
- **Text Chunking**: Sliding-window chunking (800 characters, 150-character overlap) with metadata preservation.
- **Vector Embeddings**: 768-dimensional semantic embeddings generated using Google's embedding model.
- **pgvector Cosine Search**: Rapid `<->` distance retrieval directly inside Neon PostgreSQL.
- **Grounded Q&A**: Strict citation matching preventing hallucinations, with clear attribution to page numbers and document titles.

### 3. 🎯 AI Quiz Generator & Mistake-to-Mastery
- **Dynamic MCQ Generation**: Generates 4-option questions from uploaded notes or curated CS topics (OS, DBMS, DSA, Networks, AI).
- **Instant Evaluation**: Detailed pedagogical explanations, correct answer highlights, and grounded note references.
- **Mistake-to-Mastery Loop**: Tracks repeated errors, calculates topic mastery scores, and detects concept gaps.
- **Targeted Practice**: 1-click button to generate customized practice quizzes targeting specific missed concepts.

### 4. 🤖 5-Agent Multi-Agent Learning System
- **Learner Profiling Agent**: Evaluates accuracy velocity, assigns mastery tiers (*Developing*, *Progressing*, *Mastery Pioneer*), and detects knowledge gaps.
- **Curriculum Planner Agent**: Generates adaptive, multi-phase study plans with custom goals and target timelines.
- **Content Recommendation Agent**: Discovers relevant lecture excerpts from pgvector to remediate misconceptions.
- **Quiz Agent**: Synthesizes targeted evaluation quizzes for active milestones.
- **Evaluation Agent**: Grades milestone submissions, updates learning records, and advances curriculum progression.

### 5. 🟩 LeetCode / DSA Activity Heatmap
- **GitHub-Style Green Matrix**: Trailing 365-day horizontal grid with 5 intensity levels (Levels 0–4).
- **Streak Tracker**: Real-time calculation of current daily streak (with animated flame 🔥) and all-time max streak.
- **Problem Logging**: Record problems with title, platform (LeetCode, Codeforces, HackerRank, GeeksforGeeks), difficulty, topic tag, URL, and personal notes.
- **Breakdown Analytics**: Solved problem counts by difficulty (Easy, Medium, Hard) and platform.

### 6. 📅 Interactive Study Calendar
- **Monthly Matrix Engine**: Interactive 7-column calendar (Mon–Sun) with today indicators and month navigation.
- **Task Scheduling**: Plan study sessions with category tags (*DSA*, *Core CS*, *System Design*, *Revision*, *Project*), priority dots (🔴 High, 🟡 Medium, 🔵 Low), and start/end times.
- **Progress Tracking**: Real-time monthly completion rate percentage and task status filtering (*Pending*, *Completed*).
- **Inline Completion**: Check off tasks directly with automatic database synchronization.

### 7. 🔐 User Authentication & Data Isolation
- **Secure PBKDF2 Hashing**: Passwords secured with 100,000 iterations of PBKDF2-HMAC-SHA256 and 16-byte random salts.
- **JWT Session Tokens**: URL-safe HMAC-SHA256 tokens for stateless authentication.
- **Strict Data Isolation**: Every document, vector chunk, quiz attempt, DSA problem, and calendar task is scoped to the authenticated `user_id`.

---

## 🤖 Multi-Agent Learning Architecture

The multi-agent workflow operates as an autonomous collaborative loop:

```mermaid
sequenceDiagram
    autonumber
    actor Learner as 🎓 Learner
    participant Orchestrator as 🧠 Orchestrator
    participant Profiler as 🔍 Profiling Agent
    participant Planner as 🗺️ Curriculum Planner
    participant Recommender as 📚 Recommendation Agent
    participant QuizAgent as 🎯 Quiz Agent
    participant Evaluator as ⚖️ Evaluation Agent
    participant DB as ⚡ Neon pgvector

    Learner->>Orchestrator: Set Study Goal & Timeline
    Orchestrator->>Profiler: Request Diagnostic Profile
    Profiler->>DB: Query Past Quiz Attempts & Mistakes
    DB-->>Profiler: Accuracy, Mistakes & Weak Concepts
    Profiler-->>Orchestrator: Learner Profile & Misconceptions

    Orchestrator->>Recommender: Match Remediation Excerpts
    Recommender->>DB: Cosine Vector Search (<-> 768-dim)
    DB-->>Recommender: Top Grounded Excerpts
    Recommender-->>Orchestrator: Content Recommendations

    Orchestrator->>Planner: Synthesize Curriculum
    Planner-->>Orchestrator: Multi-Phase Adaptive Study Plan
    Orchestrator->>DB: Persist Plan in study_plans Table

    Learner->>Orchestrator: Start Milestone Practice
    Orchestrator->>QuizAgent: Generate Milestone Quiz
    QuizAgent->>Gemini: Prompt with Grounded Notes
    Gemini-->>QuizAgent: Targeted MCQs
    QuizAgent-->>Learner: Deliver Quiz

    Learner->>Orchestrator: Submit Quiz Answers
    Orchestrator->>Evaluator: Evaluate Submission
    Evaluator->>DB: Update LearningProgress & Attempts
    Evaluator->>DB: Advance Milestone Status (Completed)
    Evaluator-->>Learner: Updated Mastery Score & Feedback
```

---

## 💾 Database Schema (Neon PostgreSQL)

All tables run on Neon Serverless PostgreSQL with the `pgvector` extension:

| Table Name | Primary Columns | Purpose |
|---|---|---|
| `users` | `id`, `user_id`, `username`, `email`, `hashed_password`, `full_name` | User authentication & profile data |
| `study_documents` | `id`, `user_id`, `title`, `filename`, `file_type`, `topic`, `chunk_count` | Document metadata and indexing records |
| `document_chunks` | `id`, `document_id`, `user_id`, `chunk_index`, `content`, `embedding (vector 768)` | Note text chunks with vector embeddings |
| `quizzes` | `id`, `user_id`, `title`, `topic`, `difficulty`, `questions_json` | AI-generated quiz questions & options |
| `quiz_attempts` | `id`, `quiz_id`, `user_id`, `score`, `percentage`, `answers_json`, `feedback` | Historical quiz submission records |
| `learning_progress`| `id`, `user_id`, `topic`, `subtopic`, `mastery_score`, `mistake_count`, `trend` | Continuous topic mastery metrics |
| `study_plans` | `id`, `user_id`, `goal`, `title`, `phases_json`, `agent_trace_json` | Multi-agent personalized study plans |
| `dsa_activities` | `id`, `user_id`, `problem_title`, `platform`, `difficulty`, `topic`, `activity_date` | LeetCode/DSA problem logs for heatmaps |
| `study_tasks` | `id`, `user_id`, `title`, `category`, `task_date`, `priority`, `is_completed` | Scheduled tasks for Study Calendar |

---

## 🛠️ Tech Stack

- **Frontend**: React 18, Vite, Modern CSS3 with CSS Variables & Glassmorphism
- **Backend**: FastAPI, Python 3.13, Pydantic v2, SQLAlchemy 2.0, Uvicorn
- **Database**: Neon Cloud PostgreSQL with `pgvector`
- **AI Models**: Google Gemini 3.8 Flash (`gemini-3.8-flash`), `text-embedding-004`
- **Security**: PBKDF2-HMAC-SHA256 (100k iterations), RFC 7519 JWT

---

## 🔌 API Reference

### Authentication
- `POST /api/auth/signup` — Register a new account with PBKDF2 hash.
- `POST /api/auth/login` — Authenticate credentials and receive JWT access token.
- `GET /api/auth/me` — Retrieve current authenticated user profile.
- `POST /api/auth/logout` — Invalidate user session.

### Study Notes & RAG
- `POST /api/documents/upload` — Upload PDF/TXT/MD notes, chunk text, and store 768-dim embeddings.
- `GET /api/documents` — List uploaded study documents for a user.
- `DELETE /api/documents/{id}` — Delete document and associated vector chunks.
- `POST /api/rag/ask` — Ask questions answered strictly from retrieved note chunks.

### Quizzes & Analytics
- `POST /api/quizzes/generate` — Generate dynamic AI quiz from notes or topic.
- `POST /api/quizzes/submit` — Submit quiz answers, calculate score, and update mastery.
- `POST /api/quizzes/generate-targeted` — Generate targeted remediation quiz for weak concepts.
- `GET /api/progress/analytics` — Retrieve accuracy, weak topics, and adaptive recommendations.

### Multi-Agent System
- `GET /api/agents/status` — Operational telemetry for all 5 specialized agents.
- `GET /api/agents/profile` — Learner profiling diagnosis and velocity metrics.
- `POST /api/agents/study-plan` — Synthesize personalized multi-phase curriculum.
- `PATCH /api/agents/study-plan/milestone` — Update milestone completion state.
- `POST /api/agents/evaluate` — Agent-driven submission grading and mastery updates.

### DSA Heatmap
- `GET /api/dsa/heatmap` — Retrieve 365-day activity grid, current streak, and statistics.
- `POST /api/dsa/log` — Record a solved algorithm problem.
- `DELETE /api/dsa/problems/{id}` — Delete a problem entry.

### Study Calendar
- `GET /api/calendar/tasks` — Fetch tasks and summary metrics for a given month.
- `POST /api/calendar/tasks` — Schedule a new study task.
- `PUT /api/calendar/tasks/{id}` — Update task details, schedule, or priority.
- `PATCH /api/calendar/tasks/{id}/toggle` — Toggle completion checkbox.
- `DELETE /api/calendar/tasks/{id}` — Remove a scheduled task.

---

## 💻 Local Installation & Setup

### 1. Clone Repository & Setup
```bash
git clone https://github.com/<YOUR_USERNAME>/cloudlearn.git
cd cloudlearn
```

### 2. Backend Setup
```bash
# Create and activate virtual environment
python -m venv backend/.venv

# Windows PowerShell:
.\backend\.venv\Scripts\Activate.ps1
# macOS / Linux:
# source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env and add your DATABASE_URL and GEMINI_API_KEY
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Run Backend Server
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Frontend App**: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- **FastAPI Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## ⚙️ Environment Variables

Create a `backend/.env` file based on `backend/.env.example`:

```env
HOST=127.0.0.1
PORT=8000
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Neon Cloud Serverless PostgreSQL with pgvector
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-sample-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
DATABASE_URL_UNPOOLED=postgresql://neondb_owner:YOUR_PASSWORD@ep-sample.us-east-2.aws.neon.tech/neondb?sslmode=require
NEON_BRANCH=main

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# JWT Secret Key
JWT_SECRET_KEY=your_secure_random_jwt_secret_key_here
```

---

## 🧪 Verification & Automated Tests

Run the complete 10-step integration verification suite:

```bash
python scratch/test_complete_integration.py
```

Test coverage includes:
1. Health check & database connection
2. User signup with PBKDF2 hashing & JWT issuance
3. Bearer token authentication (`/api/auth/me`)
4. Credential verification (`/api/auth/login`)
5. DSA problem logging & streak calculation
6. 365-day heatmap matrix & difficulty breakdowns
7. User-specific data isolation verification
8. Study calendar task creation, completion toggles, and monthly summary metrics
9. 5-Agent orchestrator operational status
10. Study notes pgvector retrieval and chunk listing

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
