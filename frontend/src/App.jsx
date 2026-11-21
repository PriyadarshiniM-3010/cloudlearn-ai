import React, { useState, useEffect } from 'react';

// Dynamically resolve API URL: uses environment variable in production, falls back to localhost in local dev
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') ? 'http://127.0.0.1:8000' : '');

const PRESET_TOPICS = [
  'General',
  'Operating Systems',
  'Data Structures & Algorithms',
  'Database Management (DBMS)',
  'AI & Large Language Models',
  'Computer Networks',
  'Career & Resume',
];

const SAMPLE_QUESTIONS = [
  { topic: 'Operating Systems', q: 'What are the Coffman conditions for a deadlock to occur according to the OS notes?' },
  { topic: 'Database Management (DBMS)', q: 'What is the query pattern for finding the Second Highest Salary according to the SQL cheat sheet?' },
  { topic: 'Data Structures & Algorithms', q: 'What is problem 4 "The Best Two Choices" and what is its constraint in the DSA test?' },
  { topic: 'AI & Large Language Models', q: 'What is LangChain and what does it simplify according to the report?' },
  { topic: 'Career & Resume', q: 'What is the candidate career objective and educational background from the resume?' },
];

export default function App() {
  // Navigation tab: 'dashboard', 'rag', 'quiz', 'mastery', 'agents', 'dsa', 'calendar'
  const [activeTab, setActiveTab] = useState('dashboard');

  // System health states
  const [healthStatus, setHealthStatus] = useState(null);
  const [progressData, setProgressData] = useState([]);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);

  // Documents & RAG states
  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [docTitle, setDocTitle] = useState('');
  const [docTopic, setDocTopic] = useState('Operating Systems');

  // Q&A states
  const [ragMode, setRagMode] = useState(true);
  const [selectedDocId, setSelectedDocId] = useState('all');
  const [question, setQuestion] = useState('');
  const [selectedTopic, setSelectedTopic] = useState('Operating Systems');
  const [asking, setAsking] = useState(false);
  const [qaResponse, setQaResponse] = useState(null);
  const [qaError, setQaError] = useState(null);

  // AI Quiz states
  const [quizSource, setQuizSource] = useState('document'); // 'document' or 'topic'
  const [quizDocId, setQuizDocId] = useState('');
  const [quizTopic, setQuizTopic] = useState('Operating Systems');
  const [quizNumQuestions, setQuizNumQuestions] = useState(5);
  const [quizDifficulty, setQuizDifficulty] = useState('intermediate');
  const [generatingQuiz, setGeneratingQuiz] = useState(false);
  const [quizGenError, setQuizGenError] = useState(null);
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [userAnswers, setUserAnswers] = useState({});
  const [submittingQuiz, setSubmittingQuiz] = useState(false);
  const [quizResult, setQuizResult] = useState(null);
  const [quizSubmitError, setQuizSubmitError] = useState(null);
  const [quizAttempts, setQuizAttempts] = useState([]);
  const [loadingAttempts, setLoadingAttempts] = useState(false);

  // Mistake-to-Mastery Analytics states
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [generatingTargeted, setGeneratingTargeted] = useState(false);
  const [targetedTopic, setTargetedTopic] = useState('');

  // 1. Authentication & User Profile states
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem('cloudlearn_user');
      return stored ? JSON.parse(stored) : { user_id: 'demo-user', username: 'demo-user', full_name: 'Demo Learner' };
    } catch {
      return { user_id: 'demo-user', username: 'demo-user', full_name: 'Demo Learner' };
    }
  });
  const [authToken, setAuthToken] = useState(() => {
    try {
      return localStorage.getItem('cloudlearn_token') || '';
    } catch {
      return '';
    }
  });
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'signup'
  const [authForm, setAuthForm] = useState({ username: '', email: '', password: '', full_name: '' });
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState(null);

  const activeUserId = currentUser?.user_id || currentUser?.username || 'demo-user';

  // 2. DSA Heatmap & Problem Log states
  const [dsaHeatmap, setDsaHeatmap] = useState(null);
  const [dsaLoading, setDsaLoading] = useState(false);
  const [dsaModalOpen, setDsaModalOpen] = useState(false);
  const [dsaSubmitting, setDsaSubmitting] = useState(false);
  const [dsaForm, setDsaForm] = useState({
    problem_title: '',
    platform: 'LeetCode',
    difficulty: 'Medium',
    topic: 'Arrays',
    activity_date: new Date().toISOString().slice(0, 10),
    problem_url: '',
    notes: '',
  });
  const [dsaHoveredDay, setDsaHoveredDay] = useState(null);

  // 3. Study Calendar states
  const [calendarDate, setCalendarDate] = useState(new Date());
  const [calendarTasks, setCalendarTasks] = useState([]);
  const [calendarSummary, setCalendarSummary] = useState(null);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarCategoryFilter, setCalendarCategoryFilter] = useState('all');
  const [calendarStatusFilter, setCalendarStatusFilter] = useState('all');
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [taskSubmitting, setTaskSubmitting] = useState(false);
  const [taskForm, setTaskForm] = useState({
    title: '',
    category: 'DSA',
    task_date: new Date().toISOString().slice(0, 10),
    start_time: '14:00',
    end_time: '15:30',
    priority: 'medium',
    description: '',
  });

  // Multi-Agent Learning System states
  const [agentStatus, setAgentStatus] = useState(null);
  const [learnerProfile, setLearnerProfile] = useState(null);
  const [studyPlan, setStudyPlan] = useState(null);
  const [loadingStudyPlan, setLoadingStudyPlan] = useState(false);
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [studyPlanGoal, setStudyPlanGoal] = useState('Core Computer Science Placement & Tech Interview Mastery');
  const [studyPlanTimeline, setStudyPlanTimeline] = useState('2 Weeks');
  const [studyPlanFocusTopics, setStudyPlanFocusTopics] = useState([
    'Operating Systems',
    'AI & Large Language Models',
    'Database Management (DBMS)',
  ]);
  const [activeMilestoneId, setActiveMilestoneId] = useState(null);
  const [lastAgentEvaluation, setLastAgentEvaluation] = useState(null);
  const [remediatingTopic, setRemediatingTopic] = useState('');
  const [agentActionMessage, setAgentActionMessage] = useState(null);
  const [expandedTrace, setExpandedTrace] = useState(false);

  const getFormattedMonth = (d) => {
    const yr = d.getFullYear();
    const mo = String(d.getMonth() + 1).padStart(2, '0');
    return `${yr}-${mo}`;
  };

  // Initial & User-Scoped data loading
  const fetchDocuments = async (uid = activeUserId) => {
    setDocsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents?user_id=${encodeURIComponent(uid)}`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
        if (data.length > 0 && !quizDocId) {
          setQuizDocId(String(data[0].id));
        }
      }
    } catch (e) {
      console.warn('Could not fetch documents:', e);
    } finally {
      setDocsLoading(false);
    }
  };

  const fetchProgress = async (uid = activeUserId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/progress?user_id=${encodeURIComponent(uid)}`);
      if (res.ok) {
        const data = await res.json();
        setProgressData(data);
      }
    } catch (e) {
      console.warn('Could not fetch progress:', e);
    }
  };

  const fetchQuizAttempts = async (uid = activeUserId) => {
    setLoadingAttempts(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/quizzes/attempts/history?user_id=${encodeURIComponent(uid)}`);
      if (res.ok) {
        const data = await res.json();
        setQuizAttempts(data);
      }
    } catch (e) {
      console.warn('Could not fetch quiz attempts:', e);
    } finally {
      setLoadingAttempts(false);
    }
  };

  const fetchAnalytics = async (uid = activeUserId) => {
    setLoadingAnalytics(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/progress/analytics?user_id=${encodeURIComponent(uid)}`);
      if (res.ok) {
        const data = await res.json();
        setAnalyticsData(data);
      }
    } catch (e) {
      console.warn('Could not fetch analytics:', e);
    } finally {
      setLoadingAnalytics(false);
    }
  };

  const fetchAgentStatus = async (uid = activeUserId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/agents/status?user_id=${encodeURIComponent(uid)}`);
      if (res.ok) {
        const data = await res.json();
        setAgentStatus(data);
      }
    } catch (e) {
      console.warn('Could not fetch agent status:', e);
    }
  };

  const fetchLearnerProfile = async (uid = activeUserId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/agents/profile?user_id=${encodeURIComponent(uid)}`);
      if (res.ok) {
        const data = await res.json();
        setLearnerProfile(data);
      }
    } catch (e) {
      console.warn('Could not fetch learner profile:', e);
    }
  };

  const fetchStudyPlan = async (uid = activeUserId) => {
    setLoadingStudyPlan(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/agents/study-plan?user_id=${encodeURIComponent(uid)}`);
      if (res.ok) {
        const data = await res.json();
        setStudyPlan(data);
      }
    } catch (e) {
      console.warn('Could not fetch study plan:', e);
    } finally {
      setLoadingStudyPlan(false);
    }
  };

  const fetchDsaHeatmap = async (uid = activeUserId) => {
    setDsaLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/dsa/heatmap?user_id=${encodeURIComponent(uid)}`);
      if (res.ok) {
        const data = await res.json();
        setDsaHeatmap(data);
      }
    } catch (e) {
      console.warn('Could not fetch DSA heatmap:', e);
    } finally {
      setDsaLoading(false);
    }
  };

  const fetchCalendarTasks = async (month = getFormattedMonth(calendarDate), uid = activeUserId) => {
    setCalendarLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/calendar/tasks?user_id=${encodeURIComponent(uid)}&month=${encodeURIComponent(month)}`);
      if (res.ok) {
        const data = await res.json();
        setCalendarTasks(data.tasks || []);
        setCalendarSummary(data.summary || null);
      }
    } catch (e) {
      console.warn('Could not fetch calendar tasks:', e);
    } finally {
      setCalendarLoading(false);
    }
  };

  const reloadAllUserData = (uid) => {
    fetchDocuments(uid);
    fetchProgress(uid);
    fetchQuizAttempts(uid);
    fetchAnalytics(uid);
    fetchAgentStatus(uid);
    fetchLearnerProfile(uid);
    fetchStudyPlan(uid);
    fetchDsaHeatmap(uid);
    fetchCalendarTasks(getFormattedMonth(calendarDate), uid);
  };

  useEffect(() => {
    reloadAllUserData(activeUserId);
    checkBackendHealth();
  }, [activeUserId]);

  const checkBackendHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setHealthStatus(data);
      setLastChecked(new Date().toLocaleTimeString());
      fetchProgress();
      fetchDocuments();
    } catch (err) {
      setHealthStatus(null);
      setHealthError(err.message || 'Failed to connect to backend');
      setLastChecked(new Date().toLocaleTimeString());
    } finally {
      setHealthLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (docTitle.trim()) formData.append('title', docTitle.trim());
    if (docTopic) formData.append('topic', docTopic);
    formData.append('user_id', activeUserId);

    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      setUploadSuccess(`Indexed "${data.title}" successfully into Neon pgvector (${data.chunk_count} chunks)!`);
      setSelectedFile(null);
      setDocTitle('');
      const fileInput = document.getElementById('note-file-input');
      if (fileInput) fileInput.value = '';

      fetchDocuments(activeUserId);
    } catch (err) {
      setUploadError(err.message || 'Failed to upload and index document');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (id, title) => {
    if (!window.confirm(`Delete "${title}" and remove its vector embeddings?`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/${id}?user_id=${encodeURIComponent(activeUserId)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchDocuments(activeUserId);
        if (selectedDocId === String(id)) setSelectedDocId('all');
        if (quizDocId === String(id)) setQuizDocId('');
      }
    } catch (e) {
      console.error('Delete document failed:', e);
    }
  };

  const handleAskQuestion = async (e) => {
    if (e) e.preventDefault();
    if (!question.trim()) return;

    setAsking(true);
    setQaError(null);
    try {
      let endpoint = `${API_BASE_URL}/api/ask`;
      let payload = {
        question: question.trim(),
        topic: selectedTopic === 'General' ? null : selectedTopic,
      };

      if (ragMode) {
        endpoint = `${API_BASE_URL}/api/rag/ask`;
        payload = {
          question: question.trim(),
          user_id: activeUserId,
          document_id: selectedDocId === 'all' ? null : parseInt(selectedDocId),
          topic: selectedTopic === 'General' ? null : selectedTopic,
        };
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Request failed with status ${res.status}`);
      }
      setQaResponse(data);
    } catch (err) {
      setQaError(err.message || 'Failed to generate explanation');
    } finally {
      setAsking(false);
    }
  };

  // QUIZ HANDLERS
  const handleGenerateQuiz = async (e) => {
    e.preventDefault();
    setGeneratingQuiz(true);
    setQuizGenError(null);
    setActiveQuiz(null);
    setQuizResult(null);
    setUserAnswers({});

    try {
      const payload = {
        user_id: activeUserId,
        num_questions: parseInt(quizNumQuestions) || 5,
        difficulty: quizDifficulty,
        topic: quizSource === 'topic' ? quizTopic : null,
        document_id: quizSource === 'document' && quizDocId ? parseInt(quizDocId) : null,
      };

      const res = await fetch(`${API_BASE_URL}/api/quizzes/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Quiz generation failed');
      }

      setActiveQuiz(data);
      setUserAnswers({});
    } catch (err) {
      setQuizGenError(err.message || 'Failed to generate AI quiz');
    } finally {
      setGeneratingQuiz(false);
    }
  };

  const handleSelectOption = (questionId, optionIndex) => {
    setUserAnswers((prev) => ({
      ...prev,
      [String(questionId)]: optionIndex,
    }));
  };

  const handleSubmitQuiz = async () => {
    if (!activeQuiz) return;

    const answeredCount = Object.keys(userAnswers).length;
    if (answeredCount < activeQuiz.questions.length) {
      const confirmSubmit = window.confirm(
        `You have answered ${answeredCount} of ${activeQuiz.questions.length} questions. Submit anyway?`
      );
      if (!confirmSubmit) return;
    }

    setSubmittingQuiz(true);
    setQuizSubmitError(null);

    try {
      if (activeMilestoneId) {
        // Evaluate through Evaluation Agent with knowledge gap analysis & milestone auto-update
        const payload = {
          quiz_id: activeQuiz.id,
          user_id: activeUserId,
          answers: userAnswers,
          milestone_id: activeMilestoneId,
        };

        const res = await fetch(`${API_BASE_URL}/api/agents/evaluate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Evaluation Agent evaluation failed');
        }

        const evalObj = data.evaluation;
        setLastAgentEvaluation(evalObj);
        setQuizResult({
          score: evalObj.score,
          total_questions: evalObj.total_questions,
          percentage: evalObj.percentage,
          feedback: evalObj.feedback || evalObj.next_pedagogical_action,
          mastery_status: evalObj.mastery_status || (evalObj.percentage >= 80 ? 'mastered' : 'in_progress'),
          results: evalObj.results || [],
          attempt_id: evalObj.attempt_id,
        });

        if (data.active_study_plan) {
          setStudyPlan(data.active_study_plan);
        }
      } else {
        const payload = {
          quiz_id: activeQuiz.id,
          user_id: activeUserId,
          answers: userAnswers,
        };

        const res = await fetch(`${API_BASE_URL}/api/quizzes/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Failed to evaluate quiz submission');
        }

        setQuizResult(data);
        setLastAgentEvaluation(null);
      }

      fetchProgress(activeUserId);
      fetchQuizAttempts(activeUserId);
      fetchAnalytics(activeUserId);
      fetchLearnerProfile(activeUserId);
      fetchStudyPlan(activeUserId);
    } catch (err) {
      setQuizSubmitError(err.message || 'Quiz submission failed');
    } finally {
      setSubmittingQuiz(false);
    }
  };

  const handleGenerateStudyPlan = async (e) => {
    if (e) e.preventDefault();
    setGeneratingPlan(true);
    setAgentActionMessage(null);
    try {
      const payload = {
        user_id: activeUserId,
        goal: studyPlanGoal,
        target_timeline: studyPlanTimeline,
        focus_topics: studyPlanFocusTopics,
      };

      const res = await fetch(`${API_BASE_URL}/api/agents/study-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate study plan');
      }

      setStudyPlan(data);
      setAgentActionMessage('Personalized adaptive study plan successfully synthesized by Curriculum Planner Agent!');
      fetchLearnerProfile(activeUserId);
      fetchAgentStatus(activeUserId);
    } catch (err) {
      alert(`Could not generate study plan: ${err.message}`);
    } finally {
      setGeneratingPlan(false);
    }
  };

  const handleUpdateMilestoneStatus = async (milestoneId, newStatus) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/agents/study-plan/milestone`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: activeUserId,
          milestone_id: milestoneId,
          new_status: newStatus,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setStudyPlan(data);
      }
    } catch (e) {
      console.error('Update milestone status failed:', e);
    }
  };

  const handleStartMilestonePractice = async (milestone) => {
    setRemediatingTopic(milestone.topic || 'Computer Science');
    setActiveMilestoneId(milestone.id);
    setQuizResult(null);
    setLastAgentEvaluation(null);
    try {
      await handleUpdateMilestoneStatus(milestone.id, 'in_progress');

      const res = await fetch(`${API_BASE_URL}/api/agents/remediate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: activeUserId,
          topic: milestone.topic,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate milestone practice quiz');
      }

      setActiveQuiz(data.quiz);
      setUserAnswers({});
      setActiveTab('quiz');
      window.scrollTo({ top: 380, behavior: 'smooth' });
    } catch (err) {
      alert(`Could not start milestone practice: ${err.message}`);
    } finally {
      setRemediatingTopic('');
    }
  };

  const handleRemediateWeakTopic = async (topic) => {
    setRemediatingTopic(topic);
    setActiveMilestoneId(null);
    setQuizResult(null);
    setLastAgentEvaluation(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/agents/remediate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: activeUserId,
          topic: topic,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate targeted remediation quiz');
      }

      setActiveQuiz(data.quiz);
      setUserAnswers({});
      setActiveTab('quiz');
      window.scrollTo({ top: 380, behavior: 'smooth' });
    } catch (err) {
      alert(`Could not remediate topic: ${err.message}`);
    } finally {
      setRemediatingTopic('');
    }
  };

  const handleAskAboutNote = (rec) => {
    setSelectedTopic(rec.topic || 'General');
    setQuestion(`Explain what the notes say about: ${rec.rationale || rec.document_title}`);
    setActiveTab('rag');
    window.scrollTo({ top: 350, behavior: 'smooth' });
  };

  const handleGenerateTargetedQuiz = async (topic, focusConcepts = null) => {
    setGeneratingTargeted(true);
    setTargetedTopic(topic);
    try {
      const payload = {
        topic: topic,
        focus_concepts: focusConcepts && focusConcepts.length > 0 ? focusConcepts : null,
        num_questions: 3,
        user_id: activeUserId,
      };

      const res = await fetch(`${API_BASE_URL}/api/quizzes/generate-targeted`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate targeted quiz');
      }

      setActiveQuiz(data);
      setUserAnswers({});
      setQuizResult(null);
      setLastAgentEvaluation(null);
      setActiveMilestoneId(null);
      setActiveTab('quiz');
      window.scrollTo({ top: 380, behavior: 'smooth' });
    } catch (err) {
      alert(`Could not generate targeted quiz: ${err.message}`);
    } finally {
      setGeneratingTargeted(false);
      setTargetedTopic('');
    }
  };

  // ========================================================
  // FEATURE 1: AUTHENTICATION HANDLERS
  // ========================================================
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const endpoint = authMode === 'signup' ? `${API_BASE_URL}/api/auth/signup` : `${API_BASE_URL}/api/auth/login`;
      const payload = authMode === 'signup'
        ? {
            username: authForm.username.trim(),
            email: authForm.email.trim(),
            password: authForm.password,
            full_name: authForm.full_name.trim() || undefined,
          }
        : {
            username: authForm.username.trim(),
            password: authForm.password,
          };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Authentication failed with status ${res.status}`);
      }

      localStorage.setItem('cloudlearn_token', data.access_token);
      localStorage.setItem('cloudlearn_user', JSON.stringify(data.user));
      setAuthToken(data.access_token);
      setCurrentUser(data.user);
      setAuthModalOpen(false);
      setAuthForm({ username: '', email: '', password: '', full_name: '' });
      reloadAllUserData(data.user.user_id);
    } catch (err) {
      setAuthError(err.message || 'Authentication error');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      if (authToken) {
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`,
          },
        });
      }
    } catch (e) {
      console.warn('Logout API error:', e);
    } finally {
      localStorage.removeItem('cloudlearn_token');
      localStorage.removeItem('cloudlearn_user');
      setAuthToken('');
      const defaultUser = { user_id: 'demo-user', username: 'demo-user', full_name: 'Demo Learner' };
      setCurrentUser(defaultUser);
      reloadAllUserData('demo-user');
    }
  };

  // ========================================================
  // FEATURE 2: DSA HEATMAP HANDLERS & HELPERS
  // ========================================================
  const handleLogDsaProblem = async (e) => {
    e.preventDefault();
    if (!dsaForm.problem_title.trim()) return;
    setDsaSubmitting(true);
    try {
      const payload = {
        user_id: activeUserId,
        problem_title: dsaForm.problem_title.trim(),
        platform: dsaForm.platform,
        difficulty: dsaForm.difficulty,
        topic: dsaForm.topic.trim() || 'General',
        activity_date: dsaForm.activity_date || new Date().toISOString().slice(0, 10),
        problem_url: dsaForm.problem_url.trim() || undefined,
        notes: dsaForm.notes.trim() || undefined,
      };

      const res = await fetch(`${API_BASE_URL}/api/dsa/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to log DSA problem');
      }

      setDsaModalOpen(false);
      setDsaForm({
        problem_title: '',
        platform: 'LeetCode',
        difficulty: 'Medium',
        topic: 'Arrays',
        activity_date: new Date().toISOString().slice(0, 10),
        problem_url: '',
        notes: '',
      });
      fetchDsaHeatmap(activeUserId);
    } catch (err) {
      alert(`Could not log problem: ${err.message}`);
    } finally {
      setDsaSubmitting(false);
    }
  };

  const handleDeleteDsaProblem = async (problemId) => {
    if (!window.confirm('Delete this problem entry from your activity history?')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/dsa/problems/${problemId}?user_id=${encodeURIComponent(activeUserId)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchDsaHeatmap(activeUserId);
      }
    } catch (e) {
      console.error('Delete problem failed:', e);
    }
  };

  const groupHeatmapDaysIntoWeeks = (days = []) => {
    if (!days || days.length === 0) return [];
    const weeks = [];
    let currentWeek = [];

    const firstDay = days[0];
    const initialPadding = firstDay ? firstDay.day_of_week : 0;

    for (let p = 0; p < initialPadding; p++) {
      currentWeek.push(null);
    }

    for (const day of days) {
      currentWeek.push(day);
      if (currentWeek.length === 7) {
        weeks.push(currentWeek);
        currentWeek = [];
      }
    }

    if (currentWeek.length > 0) {
      while (currentWeek.length < 7) {
        currentWeek.push(null);
      }
      weeks.push(currentWeek);
    }

    return weeks;
  };

  // ========================================================
  // FEATURE 3: STUDY CALENDAR HANDLERS & HELPERS
  // ========================================================
  const handlePrevMonth = () => {
    const newDate = new Date(calendarDate.getFullYear(), calendarDate.getMonth() - 1, 1);
    setCalendarDate(newDate);
    fetchCalendarTasks(getFormattedMonth(newDate), activeUserId);
  };

  const handleNextMonth = () => {
    const newDate = new Date(calendarDate.getFullYear(), calendarDate.getMonth() + 1, 1);
    setCalendarDate(newDate);
    fetchCalendarTasks(getFormattedMonth(newDate), activeUserId);
  };

  const handleTodayMonth = () => {
    const newDate = new Date();
    setCalendarDate(newDate);
    fetchCalendarTasks(getFormattedMonth(newDate), activeUserId);
  };

  const handleOpenCreateTask = (dateStr = null) => {
    setEditingTask(null);
    setTaskForm({
      title: '',
      category: 'DSA',
      task_date: dateStr || new Date().toISOString().slice(0, 10),
      start_time: '14:00',
      end_time: '15:30',
      priority: 'medium',
      description: '',
    });
    setTaskModalOpen(true);
  };

  const handleOpenEditTask = (task) => {
    setEditingTask(task);
    setTaskForm({
      title: task.title,
      category: task.category,
      task_date: task.task_date,
      start_time: task.start_time || '',
      end_time: task.end_time || '',
      priority: task.priority || 'medium',
      description: task.description || '',
    });
    setTaskModalOpen(true);
  };

  const handleSaveTask = async (e) => {
    e.preventDefault();
    if (!taskForm.title.trim()) return;
    setTaskSubmitting(true);
    try {
      const payload = {
        user_id: activeUserId,
        title: taskForm.title.trim(),
        category: taskForm.category,
        task_date: taskForm.task_date,
        start_time: taskForm.start_time.trim() || undefined,
        end_time: taskForm.end_time.trim() || undefined,
        priority: taskForm.priority,
        description: taskForm.description.trim() || undefined,
      };

      let endpoint = `${API_BASE_URL}/api/calendar/tasks`;
      let method = 'POST';
      if (editingTask) {
        endpoint = `${API_BASE_URL}/api/calendar/tasks/${editingTask.id}`;
        method = 'PUT';
      }

      const res = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to save study task');
      }

      setTaskModalOpen(false);
      setEditingTask(null);
      fetchCalendarTasks(getFormattedMonth(calendarDate), activeUserId);
    } catch (err) {
      alert(`Could not save task: ${err.message}`);
    } finally {
      setTaskSubmitting(false);
    }
  };

  const handleToggleTask = async (taskId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/calendar/tasks/${taskId}/toggle?user_id=${encodeURIComponent(activeUserId)}`, {
        method: 'PATCH',
      });
      if (res.ok) {
        fetchCalendarTasks(getFormattedMonth(calendarDate), activeUserId);
      }
    } catch (e) {
      console.error('Toggle task failed:', e);
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Delete this scheduled study task?')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/calendar/tasks/${taskId}?user_id=${encodeURIComponent(activeUserId)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchCalendarTasks(getFormattedMonth(calendarDate), activeUserId);
      }
    } catch (e) {
      console.error('Delete task failed:', e);
    }
  };

  const generateMonthMatrix = (dateObj) => {
    const year = dateObj.getFullYear();
    const month = dateObj.getMonth();

    const firstDay = new Date(year, month, 1);
    let startDayOfWeek = firstDay.getDay() - 1;
    if (startDayOfWeek === -1) startDayOfWeek = 6;

    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();

    const cells = [];

    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const dayNum = daysInPrevMonth - i;
      const prevMo = month === 0 ? 12 : month;
      const prevYr = month === 0 ? year - 1 : year;
      const dateStr = `${prevYr}-${String(prevMo).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
      cells.push({
        dateStr,
        dayNum,
        isCurrentMonth: false,
      });
    }

    const todayStr = new Date().toISOString().slice(0, 10);
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      cells.push({
        dateStr,
        dayNum: d,
        isCurrentMonth: true,
        isToday: dateStr === todayStr,
      });
    }

    let nextMonthDay = 1;
    while (cells.length % 7 !== 0) {
      const nextMo = month === 11 ? 1 : month + 2;
      const nextYr = month === 11 ? year + 1 : year;
      const dateStr = `${nextYr}-${String(nextMo).padStart(2, '0')}-${String(nextMonthDay).padStart(2, '0')}`;
      cells.push({
        dateStr,
        dayNum: nextMonthDay,
        isCurrentMonth: false,
      });
      nextMonthDay++;
    }

    return cells;
  };

  const handleRetakeQuiz = () => {
    setQuizResult(null);
    setUserAnswers({});
    setQuizSubmitError(null);
    setLastAgentEvaluation(null);
  };

  const selectPreset = (sample) => {
    setSelectedTopic(sample.topic);
    setQuestion(sample.q);
    if (activeTab !== 'rag') setActiveTab('rag');
  };

  const answeredQuestionsCount = Object.keys(userAnswers).length;

  return (
    <div className="page-container">
      {/* Navbar */}
      <nav className="navbar">
        <div className="brand">
          <span className="brand-logo">🎓</span>
          <span className="brand-name">CloudLearn AI</span>
        </div>
        <div className="nav-badges" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="badge badge-version">v0.7.0</span>

          {currentUser && currentUser.username !== 'demo-user' ? (
            <div className="user-profile-badge">
              <div className="user-avatar-circle" title={currentUser.email || currentUser.username}>
                {(currentUser.full_name || currentUser.username).slice(0, 2).toUpperCase()}
              </div>
              <div className="user-info-text">
                <span className="user-name">{currentUser.full_name || currentUser.username}</span>
                <span className="user-role">@{currentUser.username}</span>
              </div>
              <button
                type="button"
                className="btn-logout-nav"
                onClick={handleLogout}
                title="Log out of current account"
              >
                Log Out
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="badge" style={{ background: '#21262d', color: '#8b949e', border: '1px solid #30363d' }}>
                👤 Guest (demo-user)
              </span>
              <button
                type="button"
                className="btn-auth-nav"
                onClick={() => {
                  setAuthMode('login');
                  setAuthModalOpen(true);
                  setAuthError(null);
                }}
              >
                Sign In / Sign Up
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {/* Hero */}
        <header className="hero">
          <div className="hero-pill">Multi-Agent Personalized Learning Platform</div>
          <h1 className="hero-title">CloudLearn AI</h1>
          <p className="hero-subtitle">
            Upload notes, ask grounded questions, receive targeted practice, track LeetCode streaks, schedule tasks, and let 5 specialized AI agents coordinate your complete mistake-to-mastery journey.
          </p>

          {/* Navigation Tab Bar */}
          <div className="tab-nav-bar">
            <button
              type="button"
              className={`tab-nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              🏠 Dashboard
            </button>
            <button
              type="button"
              className={`tab-nav-btn ${activeTab === 'rag' ? 'active' : ''}`}
              onClick={() => setActiveTab('rag')}
            >
              📚 Notes & RAG Q&A
            </button>
            <button
              type="button"
              className={`tab-nav-btn ${activeTab === 'quiz' ? 'active' : ''}`}
              onClick={() => setActiveTab('quiz')}
            >
              🎯 AI Quiz Generator & Practice
            </button>
            <button
              type="button"
              className={`tab-nav-btn ${activeTab === 'mastery' ? 'active' : ''}`}
              onClick={() => setActiveTab('mastery')}
            >
              📊 Mastery & Progress ({progressData.length})
            </button>
            <button
              type="button"
              className={`tab-nav-btn ${activeTab === 'agents' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('agents');
                fetchAgentStatus(activeUserId);
                fetchLearnerProfile(activeUserId);
                fetchStudyPlan(activeUserId);
              }}
            >
              🤖 Multi-Agent Study Hub
            </button>
            <button
              type="button"
              className={`tab-nav-btn ${activeTab === 'dsa' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('dsa');
                fetchDsaHeatmap(activeUserId);
              }}
            >
              🟩 DSA Heatmap
            </button>
            <button
              type="button"
              className={`tab-nav-btn ${activeTab === 'calendar' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('calendar');
                fetchCalendarTasks(getFormattedMonth(calendarDate), activeUserId);
              }}
            >
              📅 Study Calendar
            </button>
          </div>
        </header>

        {/* ======================================================== */}
        {/* TAB 0: EXECUTIVE COMMAND CENTER DASHBOARD                */}
        {/* ======================================================== */}
        {activeTab === 'dashboard' && (
          <>
            {/* 1. PERSONALIZED WELCOME & STATUS BANNER */}
            <div className="dash-welcome-banner">
              <div>
                <div className="dash-welcome-title">
                  <span>👋</span>
                  <span>Welcome back, {currentUser?.full_name || currentUser?.username || 'Learner'}!</span>
                </div>
                <div className="dash-welcome-subtitle">
                  Your personalized AI learning workspace is synchronized with Neon pgvector, Gemini 3.8 Flash, and 5 collaborating pedagogical agents.
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                <div className="badge" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}>
                  <span className="dsa-streak-fire">🔥</span> {dsaHeatmap?.current_streak ?? 0} Day Streak
                </div>
                <div className="badge badge-phase" style={{ fontSize: '0.82rem', padding: '0.4rem 0.75rem' }}>
                  🤖 5 AI Agents Operational
                </div>
                <div className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}>
                  ⚡ Neon Cloud Connected
                </div>
              </div>
            </div>

            {/* 2. 4 EXECUTIVE PILLAR CARDS */}
            <div className="dash-kpi-grid">
              {/* Pillar 1: Study Notes RAG */}
              <div className="dash-kpi-card">
                <div>
                  <div className="dash-kpi-header">
                    <div className="dash-kpi-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
                      📚
                    </div>
                    <span className="badge badge-version" style={{ fontSize: '0.7rem' }}>pgvector</span>
                  </div>
                  <div className="dash-kpi-val">{documents.length} Notes</div>
                  <div className="dash-kpi-lbl">Study Knowledge Base</div>
                  <div className="dash-kpi-sub">
                    {documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0)} semantic 768-dim vector chunks indexed
                  </div>
                </div>
                <button
                  type="button"
                  className="dash-kpi-btn"
                  onClick={() => setActiveTab('rag')}
                >
                  Browse Notes & Ask AI &rarr;
                </button>
              </div>

              {/* Pillar 2: AI Quizzes & Mastery */}
              <div className="dash-kpi-card">
                <div>
                  <div className="dash-kpi-header">
                    <div className="dash-kpi-icon" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
                      🎯
                    </div>
                    <span className="badge" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#7dd3fc', fontSize: '0.7rem' }}>
                      {analyticsData?.summary?.overall_accuracy ?? 0}% Accuracy
                    </span>
                  </div>
                  <div className="dash-kpi-val">{quizAttempts.length} Quizzes</div>
                  <div className="dash-kpi-lbl">Mistake-to-Mastery</div>
                  <div className="dash-kpi-sub">
                    {analyticsData?.summary?.mastered_topics_count ?? 0} topics mastered &bull; {analyticsData?.summary?.total_questions_answered ?? 0} questions answered
                  </div>
                </div>
                <button
                  type="button"
                  className="dash-kpi-btn"
                  onClick={() => setActiveTab('quiz')}
                >
                  Generate Practice Quiz &rarr;
                </button>
              </div>

              {/* Pillar 3: LeetCode & DSA Activity */}
              <div className="dash-kpi-card">
                <div>
                  <div className="dash-kpi-header">
                    <div className="dash-kpi-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
                      🟩
                    </div>
                    <span className="badge badge-easy" style={{ fontSize: '0.7rem' }}>
                      Streak: {dsaHeatmap?.current_streak ?? 0}d
                    </span>
                  </div>
                  <div className="dash-kpi-val">{dsaHeatmap?.total_problems ?? 0} Solved</div>
                  <div className="dash-kpi-lbl">DSA & LeetCode Heatmap</div>
                  <div className="dash-kpi-sub">
                    {dsaHeatmap?.active_days_count ?? 0} active days &bull; Max streak: {dsaHeatmap?.max_streak ?? 0} days
                  </div>
                </div>
                <button
                  type="button"
                  className="dash-kpi-btn"
                  onClick={() => setActiveTab('dsa')}
                >
                  View 365-Day Activity &rarr;
                </button>
              </div>

              {/* Pillar 4: Study Calendar */}
              <div className="dash-kpi-card">
                <div>
                  <div className="dash-kpi-header">
                    <div className="dash-kpi-icon" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
                      📅
                    </div>
                    <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#d8b4fe', fontSize: '0.7rem' }}>
                      {calendarSummary?.completion_rate ?? 0}% Rate
                    </span>
                  </div>
                  <div className="dash-kpi-val">
                    {calendarSummary?.completed_tasks ?? 0} / {calendarSummary?.total_tasks ?? 0} Tasks
                  </div>
                  <div className="dash-kpi-lbl">Study Calendar Plan</div>
                  <div className="dash-kpi-sub">
                    {calendarSummary?.pending_tasks ?? 0} tasks pending this month
                  </div>
                </div>
                <button
                  type="button"
                  className="dash-kpi-btn"
                  onClick={() => setActiveTab('calendar')}
                >
                  Manage Schedule &rarr;
                </button>
              </div>
            </div>

            {/* 3. 2-COLUMN COMMAND CENTER GRID */}
            <div className="dash-2col-grid">
              {/* Left Column: Today's Tasks & AI Study Recommendation */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {/* Widget 1: Today's Tasks */}
                <div className="dash-widget">
                  <div className="dash-widget-header">
                    <div className="dash-widget-title">
                      <span>📅</span> Today's Study Schedule ({new Date().toISOString().slice(0, 10)})
                    </div>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                      onClick={() => handleOpenCreateTask(new Date().toISOString().slice(0, 10))}
                    >
                      + Add Task
                    </button>
                  </div>

                  {(() => {
                    const todayStr = new Date().toISOString().slice(0, 10);
                    const todayTasks = calendarTasks.filter((t) => t.task_date === todayStr);

                    if (todayTasks.length === 0) {
                      return (
                        <div style={{ textAlign: 'center', padding: '2rem 1rem', color: '#94a3b8', fontSize: '0.88rem' }}>
                          <p>🎉 All caught up! No tasks scheduled for today.</p>
                          <button
                            type="button"
                            className="btn-primary"
                            style={{ fontSize: '0.8rem', padding: '0.4rem 0.9rem', marginTop: '0.75rem' }}
                            onClick={() => handleOpenCreateTask(todayStr)}
                          >
                            + Schedule a Task for Today
                          </button>
                        </div>
                      );
                    }

                    return (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {todayTasks.map((t) => (
                          <div
                            key={t.id}
                            className={`cal-task-pill ${t.is_completed ? 'is-done' : ''}`}
                            style={{ padding: '0.55rem 0.75rem', fontSize: '0.82rem' }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden' }}>
                              <input
                                type="checkbox"
                                checked={t.is_completed}
                                onChange={() => handleToggleTask(t.id)}
                                style={{ cursor: 'pointer', accentColor: '#10b981' }}
                              />
                              <span style={{ fontWeight: 600, color: t.is_completed ? '#94a3b8' : '#f8fafc' }}>
                                {t.title}
                              </span>
                              <span className="badge" style={{ fontSize: '0.68rem', padding: '0.1rem 0.4rem' }}>
                                {t.category}
                              </span>
                              {t.start_time && (
                                <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                                  ⏰ {t.start_time}{t.end_time ? ` - ${t.end_time}` : ''}
                                </span>
                              )}
                            </div>
                            <span
                              style={{
                                fontSize: '0.7rem',
                                color: t.priority === 'high' ? '#ef4444' : t.priority === 'low' ? '#38bdf8' : '#f59e0b',
                                fontWeight: 700,
                                textTransform: 'uppercase',
                              }}
                            >
                              {t.priority}
                            </span>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </div>

                {/* Widget 2: Adaptive AI Recommendation */}
                <div className="dash-widget">
                  <div className="dash-widget-header">
                    <div className="dash-widget-title">
                      <span>🤖</span> Multi-Agent Adaptive Focus
                    </div>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                      onClick={() => setActiveTab('agents')}
                    >
                      View Full Hub &rarr;
                    </button>
                  </div>

                  {analyticsData?.weak_topics && analyticsData.weak_topics.length > 0 ? (
                    <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '10px', padding: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', fontSize: '0.72rem' }}>
                          ⚠️ Priority Remediation
                        </span>
                        <span style={{ fontSize: '0.78rem', color: '#f87171', fontWeight: 600 }}>
                          {analyticsData.weak_topics[0].mastery_score}% Mastery
                        </span>
                      </div>
                      <h4 style={{ margin: '0 0 0.35rem 0', color: '#f8fafc', fontSize: '0.95rem' }}>
                        {analyticsData.weak_topics[0].topic}
                      </h4>
                      <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.8rem', color: '#cbd5e1' }}>
                        {analyticsData.weak_topics[0].missed_concepts?.[0]
                          ? `Key misconception identified: "${analyticsData.weak_topics[0].missed_concepts[0]}"`
                          : 'Targeted practice recommended to reinforce key concepts.'}
                      </p>
                      <button
                        type="button"
                        className="btn-practice-targeted"
                        style={{ width: '100%', justifyContent: 'center', fontSize: '0.82rem' }}
                        onClick={() => handleGenerateTargetedQuiz(analyticsData.weak_topics[0].topic, analyticsData.weak_topics[0].missed_concepts)}
                      >
                        🎯 Practice {analyticsData.weak_topics[0].topic} Now
                      </button>
                    </div>
                  ) : studyPlan?.phases?.[0]?.milestones?.[0] ? (
                    <div style={{ background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: '10px', padding: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <span className="badge badge-version" style={{ fontSize: '0.72rem' }}>
                          🎯 Current Active Milestone
                        </span>
                        <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#c7d2fe', fontSize: '0.72rem' }}>
                          Phase 1
                        </span>
                      </div>
                      <h4 style={{ margin: '0 0 0.35rem 0', color: '#f8fafc', fontSize: '0.95rem' }}>
                        {studyPlan.phases[0].milestones[0].title}
                      </h4>
                      <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.8rem', color: '#cbd5e1' }}>
                        {studyPlan.phases[0].milestones[0].objective}
                      </p>
                      <button
                        type="button"
                        className="btn-primary"
                        style={{ width: '100%', justifyContent: 'center', fontSize: '0.82rem' }}
                        onClick={() => handleStartMilestonePractice(studyPlan.phases[0].milestones[0])}
                      >
                        ⚡ Start Milestone Evaluation
                      </button>
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '1.5rem 1rem', color: '#94a3b8', fontSize: '0.85rem' }}>
                      <p>No active weaknesses detected! Ready to synthesize an adaptive multi-phase study plan?</p>
                      <button
                        type="button"
                        className="btn-primary"
                        style={{ fontSize: '0.8rem', padding: '0.4rem 0.9rem', marginTop: '0.5rem' }}
                        onClick={() => setActiveTab('agents')}
                      >
                        🤖 Synthesize Study Plan
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Mini DSA Heatmap & Recent Activity Stream */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {/* Widget 3: Mini DSA Glance */}
                <div className="dash-widget">
                  <div className="dash-widget-header">
                    <div className="dash-widget-title">
                      <span>🟩</span> Daily Problem Solving Activity
                    </div>
                    <button
                      type="button"
                      className="btn-primary"
                      style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                      onClick={() => setDsaModalOpen(true)}
                    >
                      + Log Problem
                    </button>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className="badge badge-easy" style={{ fontSize: '0.72rem' }}>
                        Easy: {dsaHeatmap?.difficulty_breakdown?.Easy ?? 0}
                      </span>
                      <span className="badge badge-medium" style={{ fontSize: '0.72rem' }}>
                        Medium: {dsaHeatmap?.difficulty_breakdown?.Medium ?? 0}
                      </span>
                      <span className="badge badge-hard" style={{ fontSize: '0.72rem' }}>
                        Hard: {dsaHeatmap?.difficulty_breakdown?.Hard ?? 0}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.78rem', color: '#f59e0b', fontWeight: 600 }}>
                      🔥 {dsaHeatmap?.current_streak ?? 0} Days Running
                    </span>
                  </div>

                  {/* Mini recent 14-day strip */}
                  <div style={{ display: 'flex', gap: '5px', justifyContent: 'space-between', background: 'rgba(0,0,0,0.3)', padding: '0.65rem 0.85rem', borderRadius: '8px', overflowX: 'auto' }}>
                    {(dsaHeatmap?.days || []).slice(-14).map((d, dIdx) => (
                      <div
                        key={dIdx}
                        className={`heatmap-cell cell-level-${d.intensity}`}
                        style={{ width: '18px', height: '18px', borderRadius: '4px' }}
                        title={`${d.problem_count} problem(s) on ${d.date}`}
                        onClick={() => {
                          setDsaForm((prev) => ({ ...prev, activity_date: d.date }));
                          setDsaModalOpen(true);
                        }}
                      />
                    ))}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', fontSize: '0.72rem', color: '#64748b' }}>
                    <span>Showing last 14 days &bull; Click to log</span>
                    <button
                      type="button"
                      onClick={() => setActiveTab('dsa')}
                      style={{ background: 'transparent', border: 'none', color: '#38bdf8', cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
                    >
                      Full 365-Day Grid &rarr;
                    </button>
                  </div>
                </div>

                {/* Widget 4: Recent Learning Activity Feed */}
                <div className="dash-widget">
                  <div className="dash-widget-header">
                    <div className="dash-widget-title">
                      <span>⚡</span> Recent Activity Feed
                    </div>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Live Updates</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
                    {/* Recent Quizzes */}
                    {quizAttempts.slice(0, 2).map((att) => (
                      <div
                        key={`quiz-${att.id}`}
                        style={{
                          background: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid rgba(255, 255, 255, 0.06)',
                          borderRadius: '8px',
                          padding: '0.6rem 0.75rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontSize: '0.8rem',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span>🎯</span>
                          <div>
                            <div style={{ fontWeight: 600, color: '#f8fafc' }}>{att.quiz_title || 'Quiz'}</div>
                            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                              {att.quiz_topic} &bull; {att.score}/{att.total_questions} Correct
                            </div>
                          </div>
                        </div>
                        <span
                          className="badge"
                          style={{
                            fontSize: '0.72rem',
                            background: att.percentage >= 80 ? 'rgba(16,185,129,0.15)' : 'rgba(56,189,248,0.15)',
                            color: att.percentage >= 80 ? '#34d399' : '#38bdf8',
                          }}
                        >
                          {Math.round(att.percentage)}%
                        </span>
                      </div>
                    ))}

                    {/* Recent DSA Problems */}
                    {(dsaHeatmap?.recent_problems || []).slice(0, 2).map((prob) => (
                      <div
                        key={`dsa-${prob.id}`}
                        style={{
                          background: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid rgba(255, 255, 255, 0.06)',
                          borderRadius: '8px',
                          padding: '0.6rem 0.75rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontSize: '0.8rem',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span>💻</span>
                          <div>
                            <div style={{ fontWeight: 600, color: '#f8fafc' }}>{prob.problem_title}</div>
                            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                              {prob.platform} &bull; {prob.topic} &bull; {prob.activity_date}
                            </div>
                          </div>
                        </div>
                        <span
                          className={`badge ${prob.difficulty === 'Easy' ? 'badge-easy' : prob.difficulty === 'Hard' ? 'badge-hard' : 'badge-medium'}`}
                          style={{ fontSize: '0.7rem' }}
                        >
                          {prob.difficulty}
                        </span>
                      </div>
                    ))}

                    {quizAttempts.length === 0 && (!dsaHeatmap?.recent_problems || dsaHeatmap.recent_problems.length === 0) && (
                      <div style={{ textAlign: 'center', padding: '1rem', color: '#64748b', fontSize: '0.82rem' }}>
                        No recent activity recorded yet. Start by taking a quiz or solving a DSA problem!
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* 4. QUICK ACTION LAUNCHPAD BAR */}
            <div className="dash-launchpad-bar">
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                ⚡ Quick Launchpad:
              </span>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="dash-launchpad-btn"
                  onClick={() => setActiveTab('rag')}
                >
                  📄 Upload Study Notes
                </button>
                <button
                  type="button"
                  className="dash-launchpad-btn"
                  onClick={() => setActiveTab('rag')}
                >
                  💬 Ask Grounded Notes
                </button>
                <button
                  type="button"
                  className="dash-launchpad-btn"
                  onClick={() => setActiveTab('quiz')}
                >
                  🎯 Generate AI Quiz
                </button>
                <button
                  type="button"
                  className="dash-launchpad-btn"
                  onClick={() => setActiveTab('mastery')}
                >
                  📊 Mistake Analytics
                </button>
                <button
                  type="button"
                  className="dash-launchpad-btn"
                  onClick={() => setActiveTab('agents')}
                >
                  🤖 Multi-Agent Hub
                </button>
                <button
                  type="button"
                  className="dash-launchpad-btn"
                  onClick={() => setDsaModalOpen(true)}
                >
                  🟩 Log DSA Problem
                </button>
                <button
                  type="button"
                  className="dash-launchpad-btn"
                  onClick={() => handleOpenCreateTask()}
                >
                  📅 Schedule Study Task
                </button>
              </div>
            </div>
          </>
        )}

        {/* ======================================================== */}
        {/* TAB 1: STUDY NOTES & RAG Q&A                            */}
        {/* ======================================================== */}
        {activeTab === 'rag' && (
          <>
            {/* 1. DOCUMENT UPLOAD & MANAGEMENT */}
            <section className="card doc-card">
              <div className="qa-header">
                <div className="section-badge">📄 Grounded Knowledge Base</div>
                <h2 className="status-title" style={{ marginTop: '0.4rem' }}>
                  Upload Study Notes & PDFs
                </h2>
                <p className="status-description">
                  Upload lecture notes or cheatsheets (PDF, TXT, MD). Chunks are indexed with 768-dim Gemini embeddings in Neon pgvector.
                </p>
              </div>

              <form onSubmit={handleFileUpload} className="upload-form">
                <div className="upload-grid">
                  <div className="form-row">
                    <label className="form-label" htmlFor="note-file-input">
                      Select File (.pdf, .txt, .md):
                    </label>
                    <input
                      id="note-file-input"
                      type="file"
                      accept=".pdf,.txt,.md"
                      className="file-input"
                      onChange={(e) => setSelectedFile(e.target.files[0] || null)}
                      required
                    />
                  </div>

                  <div className="form-row">
                    <label className="form-label" htmlFor="doc-title-input">
                      Document Title (Optional):
                    </label>
                    <input
                      id="doc-title-input"
                      type="text"
                      placeholder="e.g. Operating Systems Chapter 8"
                      className="text-input"
                      value={docTitle}
                      onChange={(e) => setDocTitle(e.target.value)}
                    />
                  </div>

                  <div className="form-row">
                    <label className="form-label" htmlFor="doc-topic-input">
                      Subject / Topic:
                    </label>
                    <select
                      id="doc-topic-input"
                      className="select-input"
                      value={docTopic}
                      onChange={(e) => setDocTopic(e.target.value)}
                    >
                      {PRESET_TOPICS.filter((t) => t !== 'General').map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-actions" style={{ marginTop: '0.75rem' }}>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={uploading || !selectedFile}
                  >
                    {uploading ? (
                      <>
                        <span className="spinner"></span>
                        Extracting & Indexing Embeddings...
                      </>
                    ) : (
                      'Upload & Index Notes 🚀'
                    )}
                  </button>
                </div>
              </form>

              {uploadSuccess && (
                <div className="alert alert-success" style={{ marginTop: '1rem' }}>
                  <div className="alert-icon">✓</div>
                  <div className="alert-details">
                    <div className="alert-heading">Document Indexed!</div>
                    <div className="alert-body">{uploadSuccess}</div>
                  </div>
                </div>
              )}

              {uploadError && (
                <div className="alert alert-error" style={{ marginTop: '1rem' }}>
                  <div className="alert-icon">⚠️</div>
                  <div className="alert-details">
                    <div className="alert-heading">Upload Failed</div>
                    <div className="alert-body">{uploadError}</div>
                  </div>
                </div>
              )}

              {/* Uploaded Documents Shelf */}
              <div className="doc-list-section">
                <h3 className="doc-list-title">
                  Indexed Study Materials ({documents.length})
                </h3>
                {docsLoading ? (
                  <div className="status-placeholder">Loading indexed documents...</div>
                ) : documents.length === 0 ? (
                  <div className="status-placeholder">
                    No documents uploaded yet. Upload a PDF or notes file above to chat with your course materials!
                  </div>
                ) : (
                  <div className="doc-grid">
                    {documents.map((doc) => (
                      <div key={doc.id} className="doc-item">
                        <div className="doc-info">
                          <div className="doc-title-row">
                            <span className="doc-icon">📑</span>
                            <strong>{doc.title}</strong>
                            {doc.topic && <span className="badge badge-phase">{doc.topic}</span>}
                          </div>
                          <div className="doc-meta">
                            {doc.filename} &bull; {doc.page_count} page(s) &bull; {doc.chunk_count} vector chunks &bull; {(doc.file_size_bytes / 1024).toFixed(1)} KB
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                          <button
                            type="button"
                            className="btn-quick-quiz"
                            title="Generate Quiz from this document"
                            onClick={() => {
                              setQuizSource('document');
                              setQuizDocId(String(doc.id));
                              setActiveTab('quiz');
                            }}
                          >
                            🎯 Quiz
                          </button>
                          <button
                            type="button"
                            className="btn-delete"
                            title="Delete document and vector chunks"
                            onClick={() => handleDeleteDocument(doc.id, doc.title)}
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            {/* 2. ASK CLOUDLEARN AI (RAG & TUTOR) */}
            <section className="card qa-card">
              <div className="qa-header">
                <div className="section-badge">✨ Grounded Vector Retrieval (pgvector) + Gemini</div>
                <h2 className="status-title" style={{ marginTop: '0.4rem' }}>
                  Ask CloudLearn AI
                </h2>
                <p className="status-description">
                  Ask questions grounded in your uploaded documents, with page citations and clear detection of missing information.
                </p>
              </div>

              {/* Mode Toggle */}
              <div className="mode-toggle-bar">
                <button
                  type="button"
                  className={`mode-btn ${ragMode ? 'active' : ''}`}
                  onClick={() => setRagMode(true)}
                >
                  📚 Ask From My Notes (Grounded Mode)
                </button>
                <button
                  type="button"
                  className={`mode-btn ${!ragMode ? 'active' : ''}`}
                  onClick={() => setRagMode(false)}
                >
                  💡 General AI Tutor
                </button>
              </div>

              {/* Sample Prompts */}
              <div className="presets-container">
                <span className="presets-label">Targeted Prompts:</span>
                <div className="presets-list">
                  {SAMPLE_QUESTIONS.map((s, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="preset-btn"
                      onClick={() => selectPreset(s)}
                    >
                      {s.q.length > 55 ? `${s.q.substring(0, 55)}...` : s.q}
                    </button>
                  ))}
                </div>
              </div>

              <form onSubmit={handleAskQuestion} className="qa-form">
                <div className="form-row-split">
                  {ragMode && (
                    <div className="form-row" style={{ flex: 1 }}>
                      <label className="form-label" htmlFor="doc-select">
                        Target Document:
                      </label>
                      <select
                        id="doc-select"
                        className="select-input"
                        value={selectedDocId}
                        onChange={(e) => setSelectedDocId(e.target.value)}
                      >
                        <option value="all">🔍 Search Across All Uploaded Notes ({documents.length})</option>
                        {documents.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.title} ({d.chunk_count} chunks)
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="form-row" style={{ flex: 1 }}>
                    <label className="form-label" htmlFor="topic-select">
                      Topic Domain:
                    </label>
                    <select
                      id="topic-select"
                      className="select-input"
                      value={selectedTopic}
                      onChange={(e) => setSelectedTopic(e.target.value)}
                    >
                      {PRESET_TOPICS.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <textarea
                    className="qa-textarea"
                    rows={3}
                    placeholder={
                      ragMode
                        ? "Ask a question about your uploaded notes (e.g., What are the Coffman deadlock conditions according to the OS notes?)..."
                        : "Ask any concept question (e.g., Explain virtual memory simply)..."
                    }
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    required
                  />
                </div>

                <div className="form-actions">
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={asking || !question.trim()}
                  >
                    {asking ? (
                      <>
                        <span className="spinner"></span>
                        {ragMode ? 'Searching Notes & Grounding...' : 'Generating Explanation...'}
                      </>
                    ) : ragMode ? (
                      'Ask Notes (RAG) 🔍'
                    ) : (
                      'Ask AI Tutor ✨'
                    )}
                  </button>
                </div>
              </form>

              {qaError && (
                <div className="alert alert-error" style={{ marginTop: '1.25rem' }}>
                  <div className="alert-icon">⚠️</div>
                  <div className="alert-details">
                    <div className="alert-heading">Notice</div>
                    <div className="alert-body">{qaError}</div>
                  </div>
                </div>
              )}

              {/* Q&A Answer View */}
              {qaResponse && (
                <div className="qa-answer-card">
                  <div className="qa-answer-header">
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                      <span className="badge badge-version">🤖 {qaResponse.model}</span>
                      {qaResponse.has_context !== undefined && (
                        <span
                          className="badge"
                          style={{
                            background: qaResponse.has_context ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)',
                            color: qaResponse.has_context ? '#34d399' : '#fbbf24',
                            borderColor: qaResponse.has_context ? 'rgba(16,185,129,0.4)' : 'rgba(245,158,11,0.4)',
                          }}
                        >
                          {qaResponse.has_context ? '📚 Grounded in Notes' : '⚠️ Missing in Notes (General Knowledge)'}
                        </span>
                      )}
                      {qaResponse.topic && <span className="badge badge-phase">{qaResponse.topic}</span>}
                    </div>
                    <button
                      type="button"
                      className="preset-btn"
                      style={{ fontSize: '0.75rem' }}
                      onClick={() => setQaResponse(null)}
                    >
                      Clear
                    </button>
                  </div>

                  <div className="qa-question-echo">
                    <strong>Q:</strong> {qaResponse.question}
                  </div>

                  {/* Retrieved Sources Box */}
                  {qaResponse.sources && qaResponse.sources.length > 0 && (
                    <div className="sources-container">
                      <h4 className="sources-title">
                        📖 Retrieved Sources ({qaResponse.sources.length}):
                      </h4>
                      <div className="sources-list">
                        {qaResponse.sources.map((src, sIdx) => (
                          <div key={sIdx} className="source-item">
                            <div className="source-header">
                              <span className="source-doc">
                                📑 {src.document_title}
                                {src.page_number && ` (Page ${src.page_number})`}
                              </span>
                              <span className="source-score">
                                {Math.round(src.similarity_score * 100)}% match
                              </span>
                            </div>
                            <div className="source-excerpt">"{src.excerpt}"</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="qa-answer-body">
                    {qaResponse.answer.split('\n\n').map((paragraph, pIdx) => {
                      if (paragraph.startsWith('### ') || paragraph.startsWith('## ') || paragraph.startsWith('# ')) {
                        return (
                          <h4 key={pIdx} className="qa-answer-heading">
                            {paragraph.replace(/^#+\s*/, '')}
                          </h4>
                        );
                      }
                      return (
                        <p key={pIdx} className="qa-answer-p">
                          {paragraph}
                        </p>
                      );
                    })}
                  </div>
                </div>
              )}
            </section>
          </>
        )}

        {/* ======================================================== */}
        {/* TAB 2: AI QUIZ GENERATOR & PRACTICE                     */}
        {/* ======================================================== */}
        {activeTab === 'quiz' && (
          <section className="card quiz-card">
            <div className="qa-header">
              <div className="section-badge">🎯 Gemini 3.8 Flash + Adaptive Assessment</div>
              <h2 className="status-title" style={{ marginTop: '0.4rem' }}>
                AI Quiz Generator & Practice
              </h2>
              <p className="status-description">
                Generate 4-option multiple choice quizzes directly from your uploaded study notes or any computer science domain.
              </p>
            </div>

            {/* Quiz Setup Form (when not actively taking a quiz or reviewing) */}
            {!activeQuiz && !quizResult && (
              <form onSubmit={handleGenerateQuiz} className="quiz-generator-form">
                <div className="quiz-setup-grid">
                  {/* Source selector */}
                  <div className="form-row">
                    <label className="form-label">Quiz Generation Source:</label>
                    <div className="radio-pill-group">
                      <label className={`radio-pill ${quizSource === 'document' ? 'selected' : ''}`}>
                        <input
                          type="radio"
                          name="quizSource"
                          value="document"
                          checked={quizSource === 'document'}
                          onChange={() => setQuizSource('document')}
                        />
                        📄 From Uploaded Study Note
                      </label>
                      <label className={`radio-pill ${quizSource === 'topic' ? 'selected' : ''}`}>
                        <input
                          type="radio"
                          name="quizSource"
                          value="topic"
                          checked={quizSource === 'topic'}
                          onChange={() => setQuizSource('topic')}
                        />
                        🌐 From Subject Domain
                      </label>
                    </div>
                  </div>

                  {/* Target Document or Subject Topic */}
                  {quizSource === 'document' ? (
                    <div className="form-row">
                      <label className="form-label" htmlFor="quiz-doc-select">
                        Select Study Material:
                      </label>
                      <select
                        id="quiz-doc-select"
                        className="select-input"
                        value={quizDocId}
                        onChange={(e) => setQuizDocId(e.target.value)}
                        required
                      >
                        {documents.length === 0 ? (
                          <option value="">No notes uploaded yet</option>
                        ) : (
                          documents.map((d) => (
                            <option key={d.id} value={d.id}>
                              {d.title} ({d.page_count} pgs, {d.chunk_count} chunks)
                            </option>
                          ))
                        )}
                      </select>
                    </div>
                  ) : (
                    <div className="form-row">
                      <label className="form-label" htmlFor="quiz-topic-select">
                        Subject / Domain:
                      </label>
                      <select
                        id="quiz-topic-select"
                        className="select-input"
                        value={quizTopic}
                        onChange={(e) => setQuizTopic(e.target.value)}
                      >
                        {PRESET_TOPICS.filter((t) => t !== 'General').map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Number of Questions & Difficulty */}
                  <div className="form-row-split">
                    <div className="form-row" style={{ flex: 1 }}>
                      <label className="form-label" htmlFor="quiz-count-select">
                        Number of Questions:
                      </label>
                      <select
                        id="quiz-count-select"
                        className="select-input"
                        value={quizNumQuestions}
                        onChange={(e) => setQuizNumQuestions(parseInt(e.target.value))}
                      >
                        <option value={3}>3 Questions (Quick Sprint)</option>
                        <option value={5}>5 Questions (Standard Practice)</option>
                        <option value={10}>10 Questions (Deep Assessment)</option>
                      </select>
                    </div>

                    <div className="form-row" style={{ flex: 1 }}>
                      <label className="form-label" htmlFor="quiz-diff-select">
                        Difficulty Level:
                      </label>
                      <select
                        id="quiz-diff-select"
                        className="select-input"
                        value={quizDifficulty}
                        onChange={(e) => setQuizDifficulty(e.target.value)}
                      >
                        <option value="beginner">Beginner (Core Definitions)</option>
                        <option value="intermediate">Intermediate (Problem Solving & Logic)</option>
                        <option value="advanced">Advanced (Placement & Gate Tricky)</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="form-actions" style={{ marginTop: '1.25rem' }}>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={generatingQuiz || (quizSource === 'document' && !quizDocId)}
                  >
                    {generatingQuiz ? (
                      <>
                        <span className="spinner"></span>
                        Gemini is crafting high-yield MCQs...
                      </>
                    ) : (
                      'Generate AI Quiz ⚡'
                    )}
                  </button>
                </div>
              </form>
            )}

            {quizGenError && (
              <div className="alert alert-error" style={{ marginTop: '1rem' }}>
                <div className="alert-icon">⚠️</div>
                <div className="alert-details">
                  <div className="alert-heading">Generation Error</div>
                  <div className="alert-body">{quizGenError}</div>
                </div>
              </div>
            )}

            {/* ACTIVE QUIZ TAKING INTERFACE */}
            {activeQuiz && !quizResult && (
              <div className="active-quiz-container">
                <div className="quiz-header-bar">
                  <div>
                    <h3 className="quiz-title">{activeQuiz.title}</h3>
                    <div className="quiz-meta-row">
                      <span className="badge badge-version">Topic: {activeQuiz.topic}</span>
                      <span className="badge badge-phase">Level: {activeQuiz.difficulty}</span>
                      {activeMilestoneId && (
                        <span className="badge" style={{ background: 'rgba(99,102,241,0.25)', color: '#a5b4fc', borderColor: '#818cf8' }}>
                          🎯 Study Plan Milestone Practice
                        </span>
                      )}
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.08)' }}>
                        {answeredQuestionsCount} of {activeQuiz.questions.length} Answered
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn-exit"
                    onClick={() => {
                      if (window.confirm('Exit quiz? Your answers will not be saved.')) {
                        setActiveQuiz(null);
                        setUserAnswers({});
                      }
                    }}
                  >
                    ✕ Exit Quiz
                  </button>
                </div>

                {/* Question Cards */}
                <div className="quiz-questions-list">
                  {activeQuiz.questions.map((q, qIndex) => {
                    const isAnswered = userAnswers[String(q.id)] !== undefined;
                    return (
                      <div key={q.id} className={`quiz-q-card ${isAnswered ? 'answered' : ''}`}>
                        <div className="quiz-q-header">
                          <span className="quiz-q-number">Question {qIndex + 1} of {activeQuiz.questions.length}</span>
                          {q.source_reference && (
                            <span className="quiz-source-tag">📖 {q.source_reference}</span>
                          )}
                        </div>
                        <div className="quiz-q-text">{q.question}</div>

                        {/* Options Grid */}
                        <div className="quiz-options-grid">
                          {q.options.map((opt, optIndex) => {
                            const isSelected = userAnswers[String(q.id)] === optIndex;
                            return (
                              <button
                                key={optIndex}
                                type="button"
                                className={`quiz-option-button ${isSelected ? 'selected' : ''}`}
                                onClick={() => handleSelectOption(q.id, optIndex)}
                              >
                                <span className="option-letter">{chr(65 + optIndex)}</span>
                                <span className="option-text">{opt}</span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {quizSubmitError && (
                  <div className="alert alert-error" style={{ marginTop: '1rem' }}>
                    <div className="alert-icon">⚠️</div>
                    <div className="alert-details">
                      <div className="alert-heading">Submission Error</div>
                      <div className="alert-body">{quizSubmitError}</div>
                    </div>
                  </div>
                )}

                <div className="quiz-submit-bar">
                  <div className="submit-summary">
                    {answeredQuestionsCount === activeQuiz.questions.length ? (
                      <span style={{ color: '#34d399' }}>✓ All questions answered! Ready to submit.</span>
                    ) : (
                      <span style={{ color: '#fbbf24' }}>
                        {activeQuiz.questions.length - answeredQuestionsCount} question(s) remaining
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={submittingQuiz || answeredQuestionsCount === 0}
                    onClick={handleSubmitQuiz}
                  >
                    {submittingQuiz ? (
                      <>
                        <span className="spinner"></span>
                        Evaluating Submission...
                      </>
                    ) : (
                      'Submit Quiz & Review Answers 🚀'
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* QUIZ RESULTS & EXPLANATIONS VIEW */}
            {quizResult && (
              <div className="quiz-results-container">
                <div className="results-hero-card">
                  <div className="score-circle">
                    <span className="score-num">{Math.round(quizResult.percentage)}%</span>
                    <span className="score-label">{quizResult.score} / {quizResult.total_questions} Correct</span>
                  </div>
                  <div className="results-hero-info">
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span
                        className="badge"
                        style={{
                          background: quizResult.mastery_status === 'mastered'
                            ? 'rgba(16,185,129,0.2)'
                            : quizResult.mastery_status === 'in_progress'
                            ? 'rgba(56,189,248,0.2)'
                            : 'rgba(239,68,68,0.2)',
                          color: quizResult.mastery_status === 'mastered'
                            ? '#34d399'
                            : quizResult.mastery_status === 'in_progress'
                            ? '#7dd3fc'
                            : '#f87171',
                          fontWeight: 700,
                        }}
                      >
                        {quizResult.mastery_status.toUpperCase().replace('_', ' ')}
                      </span>
                      <span className="badge badge-version">Attempt #{quizResult.attempt_id}</span>
                    </div>
                    <h3 className="results-heading">{quizResult.feedback}</h3>
                    <p className="results-desc">
                      Your score has been logged to Neon PostgreSQL and your concept mastery has been updated. Review the detailed breakdown below:
                    </p>
                  </div>
                </div>

                {/* Multi-Agent Evaluation Agent Diagnostic Callout */}
                {lastAgentEvaluation && (
                  <div className="eval-agent-box">
                    <div className="eval-agent-header">
                      <div className="eval-agent-title">
                        🎓 {lastAgentEvaluation.evaluating_agent || 'Evaluation Agent'} &bull; Cognitive Diagnostic
                      </div>
                      {lastAgentEvaluation.milestone_id && (
                        <span
                          className="badge"
                          style={{
                            background: lastAgentEvaluation.milestone_action === 'completed' ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)',
                            color: lastAgentEvaluation.milestone_action === 'completed' ? '#34d399' : '#fbbf24',
                            fontWeight: 700,
                          }}
                        >
                          {lastAgentEvaluation.milestone_action === 'completed'
                            ? '🎉 Milestone Completed in Active Study Plan!'
                            : '⚠️ Remediation Practice Needed to Complete Milestone'}
                        </span>
                      )}
                    </div>

                    {lastAgentEvaluation.mastered_concepts && lastAgentEvaluation.mastered_concepts.length > 0 && (
                      <div style={{ marginBottom: '0.85rem' }}>
                        <div style={{ fontSize: '0.8rem', color: '#9ca3af', fontWeight: 600, marginBottom: '0.35rem' }}>
                          ✓ Confirmed Mastered Concepts:
                        </div>
                        <div className="profile-chip-list">
                          {lastAgentEvaluation.mastered_concepts.map((concept, cIdx) => (
                            <span key={cIdx} className="profile-chip profile-chip-mastered">
                              ✓ {concept}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {lastAgentEvaluation.knowledge_gaps && lastAgentEvaluation.knowledge_gaps.length > 0 && (
                      <div>
                        <div style={{ fontSize: '0.8rem', color: '#f87171', fontWeight: 600, marginBottom: '0.35rem' }}>
                          ⚠️ Identified Knowledge Gaps ({lastAgentEvaluation.knowledge_gaps.length}):
                        </div>
                        {lastAgentEvaluation.knowledge_gaps.map((gap, gIdx) => (
                          <div key={gIdx} className="eval-gap-card">
                            <div className="eval-gap-concept">
                              Misconception #{gIdx + 1}: {gap.concept}
                            </div>
                            <div className="eval-gap-comparison">
                              <div className="eval-gap-user-choice">
                                <strong>Your Choice:</strong> {gap.student_choice}
                              </div>
                              <div className="eval-gap-correct-choice">
                                <strong>Correct Principle:</strong> {gap.correct_answer}
                              </div>
                            </div>
                            <div className="eval-gap-explanation">
                              💡 <strong>Agent Analysis:</strong> {gap.explanation}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {lastAgentEvaluation.next_pedagogical_action && (
                      <div className="eval-next-action-box">
                        <span>🧭</span>
                        <span><strong>Next Pedagogical Step:</strong> {lastAgentEvaluation.next_pedagogical_action}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Review Questions Breakdown */}
                <div className="results-breakdown-list">
                  <h4 className="breakdown-title">Detailed Question Evaluation & Explanations:</h4>
                  {quizResult.results.map((r, rIdx) => (
                    <div
                      key={r.question_id}
                      className={`review-q-card ${r.is_correct ? 'is-correct' : 'is-wrong'}`}
                    >
                      <div className="review-q-header">
                        <span className="review-q-title">
                          Question {rIdx + 1}: {r.question}
                        </span>
                        <span className={`review-badge ${r.is_correct ? 'badge-correct' : 'badge-wrong'}`}>
                          {r.is_correct ? '✓ Correct' : '✗ Incorrect'}
                        </span>
                      </div>

                      <div className="review-options-list">
                        {r.options.map((opt, optIdx) => {
                          const isStudentChoice = r.selected_index === optIdx;
                          const isTheCorrectOption = r.correct_index === optIdx;
                          let optClass = 'review-option';
                          if (isTheCorrectOption) optClass += ' option-correct';
                          if (isStudentChoice && !isTheCorrectOption) optClass += ' option-wrong-choice';

                          return (
                            <div key={optIdx} className={optClass}>
                              <span className="opt-marker">
                                {isTheCorrectOption ? '✓' : isStudentChoice ? '✗' : chr(65 + optIdx)}
                              </span>
                              <span className="opt-content">
                                {opt}
                                {isStudentChoice && !isTheCorrectOption && ' (Your choice)'}
                                {isTheCorrectOption && ' (Correct answer)'}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Pedagogical Explanation Callout */}
                      <div className="review-explanation-box">
                        <div className="explanation-label">💡 Explanation:</div>
                        <div className="explanation-text">{r.explanation}</div>
                        {r.source_reference && (
                          <div className="explanation-source">
                            📖 Grounded Source: <strong>{r.source_reference}</strong>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Action buttons */}
                <div className="results-actions">
                  {quizResult.percentage < 100 && (
                    <button
                      type="button"
                      className="btn-practice-targeted"
                      onClick={() => {
                        const wrongConcepts = quizResult.results
                          .filter((r) => !r.is_correct)
                          .map((r) => r.question);
                        handleGenerateTargetedQuiz(activeQuiz?.topic || 'General', wrongConcepts);
                      }}
                      disabled={generatingTargeted}
                    >
                      {generatingTargeted ? (
                        <>
                          <span className="spinner"></span>
                          Generating Targeted Practice...
                        </>
                      ) : (
                        '🎯 Practice Weak Concepts (Targeted MCQ)'
                      )}
                    </button>
                  )}
                  <button type="button" className="btn-secondary" onClick={handleRetakeQuiz}>
                    🔄 Retake This Quiz
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => {
                      setActiveQuiz(null);
                      setQuizResult(null);
                      setUserAnswers({});
                    }}
                  >
                    ⚡ Create Another Quiz
                  </button>
                </div>
              </div>
            )}

            {/* Quiz Attempts History Shelf */}
            {!activeQuiz && (
              <div className="attempts-history-section">
                <h3 className="doc-list-title">
                  Recent Quiz Attempts ({quizAttempts.length})
                </h3>
                {loadingAttempts ? (
                  <div className="status-placeholder">Loading previous attempts...</div>
                ) : quizAttempts.length === 0 ? (
                  <div className="status-placeholder">
                    No quiz attempts recorded yet. Generate and take a quiz above to start tracking your mastery!
                  </div>
                ) : (
                  <div className="attempts-table">
                    {quizAttempts.map((att) => (
                      <div key={att.id} className="attempt-row">
                        <div className="attempt-info">
                          <span className="attempt-score-badge">
                            {Math.round(att.percentage)}%
                          </span>
                          <div>
                            <strong>{att.quiz_title || 'Quiz'}</strong> &bull; <span style={{ color: '#9ca3af' }}>{att.quiz_topic}</span>
                            <div className="attempt-meta">
                              {att.score} / {att.total_questions} Correct &bull; {new Date(att.created_at).toLocaleDateString()} at {new Date(att.created_at).toLocaleTimeString()}
                            </div>
                          </div>
                        </div>
                        <span
                          className="badge"
                          style={{
                            background: att.percentage >= 80 ? 'rgba(16,185,129,0.2)' : 'rgba(56,189,248,0.2)',
                            color: att.percentage >= 80 ? '#34d399' : '#7dd3fc',
                          }}
                        >
                          {att.percentage >= 80 ? 'Mastered' : 'Reviewed'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* ======================================================== */}
        {/* TAB 3: MASTERY & PROGRESS DASHBOARD                     */}
        {/* ======================================================== */}
        {activeTab === 'mastery' && (
          <>
            {/* 1. TOP SUMMARY METRICS CARDS */}
            <section className="stats-summary-grid">
              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
                  📝
                </div>
                <div>
                  <div className="stat-value">{analyticsData?.summary?.total_quizzes_taken ?? quizAttempts.length}</div>
                  <div className="stat-label">Quizzes Completed</div>
                  <div className="stat-sub">Across all study notes</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
                  🎯
                </div>
                <div>
                  <div className="stat-value">{analyticsData?.summary?.total_questions_answered ?? 0}</div>
                  <div className="stat-label">Questions Answered</div>
                  <div className="stat-sub">{analyticsData?.summary?.total_correct_answers ?? 0} answered correctly</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
                  📈
                </div>
                <div>
                  <div className="stat-value" style={{ color: (analyticsData?.summary?.overall_accuracy ?? 0) >= 70 ? '#34d399' : '#f59e0b' }}>
                    {analyticsData?.summary?.overall_accuracy ?? 0}%
                  </div>
                  <div className="stat-label">Overall Accuracy</div>
                  <div className="stat-sub">Across all attempts</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
                  🏆
                </div>
                <div>
                  <div className="stat-value">{analyticsData?.summary?.mastered_topics_count ?? 0}</div>
                  <div className="stat-label">Mastered Topics</div>
                  <div className="stat-sub">≥80% accuracy threshold</div>
                </div>
              </div>
            </section>

            {/* 2. WEAK TOPICS & RECURRING MISCONCEPTIONS SECTION */}
            {analyticsData?.weak_topics && analyticsData.weak_topics.length > 0 && (
              <section className="card" style={{ borderColor: 'rgba(239, 68, 68, 0.4)' }}>
                <div className="qa-header">
                  <div className="section-badge" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
                    ⚠️ Needs Attention & Remediation
                  </div>
                  <h2 className="status-title" style={{ marginTop: '0.4rem', color: '#fca5a5' }}>
                    Weak Concepts & Recurring Mistakes ({analyticsData.weak_topics.length})
                  </h2>
                  <p className="status-description">
                    Gemini analyzes your incorrect quiz submissions to pinpoint specific misconceptions. Click <strong>"Practice Weak Concepts"</strong> to generate targeted practice MCQs grounded in your uploaded notes.
                  </p>
                </div>

                <div className="weak-topics-container">
                  {analyticsData.weak_topics.map((wt, idx) => (
                    <div key={idx} className="weak-topic-item">
                      <div className="weak-topic-header">
                        <div className="weak-topic-title">
                          <span>📌 {wt.topic}</span>
                          <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>
                            {wt.mastery_score}% Accuracy ({wt.mistake_count} Mistakes)
                          </span>
                        </div>
                        <button
                          type="button"
                          className="btn-practice-targeted"
                          onClick={() => handleGenerateTargetedQuiz(wt.topic, wt.missed_concepts)}
                          disabled={generatingTargeted && targetedTopic === wt.topic}
                        >
                          {generatingTargeted && targetedTopic === wt.topic ? (
                            <>
                              <span className="spinner"></span>
                              Generating Targeted Quiz...
                            </>
                          ) : (
                            `🎯 Practice ${wt.topic} Concepts`
                          )}
                        </button>
                      </div>

                      {wt.missed_concepts && wt.missed_concepts.length > 0 && (
                        <div>
                          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f87171', marginBottom: '0.35rem' }}>
                            Identified Concept Gaps from Past Mistakes:
                          </div>
                          <ul className="weak-concepts-list">
                            {wt.missed_concepts.map((concept, cIdx) => (
                              <li key={cIdx} className="weak-concept-pill">
                                <span>⚠️</span>
                                <span>{concept}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 3. ADAPTIVE STUDY RECOMMENDATIONS */}
            {analyticsData?.next_recommendations && analyticsData.next_recommendations.length > 0 && (
              <section className="card">
                <div className="qa-header">
                  <div className="section-badge">🧭 Adaptive Learning Path</div>
                  <h2 className="status-title" style={{ marginTop: '0.4rem' }}>
                    What to Study Next (Personalized Recommendations)
                  </h2>
                  <p className="status-description">
                    Adaptive AI recommends remediation for weak areas, diagnostic quizzes on unquizzed uploaded notes, and advanced challenges for mastered concepts.
                  </p>
                </div>

                <div className="recommendations-grid">
                  {analyticsData.next_recommendations.map((rec, rIdx) => {
                    const badgeClass =
                      rec.type === 'remediate'
                        ? 'rec-badge-remediate'
                        : rec.type === 'explore'
                        ? 'rec-badge-explore'
                        : 'rec-badge-challenge';
                    const badgeLabel =
                      rec.type === 'remediate'
                        ? '🎯 Remediation'
                        : rec.type === 'explore'
                        ? '📖 Explore Notes'
                        : '🏆 Mastery Challenge';

                    return (
                      <div key={rIdx} className="rec-card">
                        <div>
                          <span className={`badge ${badgeClass}`}>{badgeLabel}</span>
                          <h4 className="rec-title">{rec.title}</h4>
                          <p className="rec-reason">{rec.reason}</p>
                        </div>
                        <div>
                          {rec.type === 'remediate' && (
                            <button
                              type="button"
                              className="btn-practice-targeted"
                              style={{ width: '100%', justifyContent: 'center' }}
                              onClick={() => handleGenerateTargetedQuiz(rec.topic)}
                              disabled={generatingTargeted && targetedTopic === rec.topic}
                            >
                              {generatingTargeted && targetedTopic === rec.topic ? (
                                <>
                                  <span className="spinner"></span>
                                  Generating...
                                </>
                              ) : (
                                '🎯 Start Targeted Practice'
                              )}
                            </button>
                          )}
                          {rec.type === 'explore' && (
                            <button
                              type="button"
                              className="btn-rec-action"
                              style={{ width: '100%' }}
                              onClick={() => {
                                if (rec.document_id) setQuizDocId(String(rec.document_id));
                                setQuizSource('document');
                                setActiveTab('quiz');
                                window.scrollTo({ top: 380, behavior: 'smooth' });
                              }}
                            >
                              📖 Generate Diagnostic Quiz
                            </button>
                          )}
                          {rec.type === 'challenge' && (
                            <button
                              type="button"
                              className="btn-rec-action"
                              style={{ width: '100%' }}
                              onClick={() => {
                                setQuizTopic(rec.topic);
                                setQuizSource('topic');
                                setQuizDifficulty('advanced');
                                setActiveTab('quiz');
                                window.scrollTo({ top: 380, behavior: 'smooth' });
                              }}
                            >
                              🏆 Push to Advanced Level
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* 4. TOPIC-WISE MASTERY PROGRESSION & TRENDS */}
            <section className="card">
              <div className="qa-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <div className="section-badge">📊 Progress & Trends</div>
                    <h2 className="status-title" style={{ marginTop: '0.4rem' }}>
                      Topic Mastery & Performance Trends
                    </h2>
                  </div>
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                    onClick={() => {
                      fetchAnalytics();
                      fetchProgress();
                      fetchQuizAttempts();
                    }}
                    disabled={loadingAnalytics}
                  >
                    {loadingAnalytics ? 'Refreshing...' : '🔄 Refresh Analytics'}
                  </button>
                </div>
                <p className="status-description">
                  Tracks topic accuracy, progress direction (improving, stable, declining), and persistent mistake logs in Neon PostgreSQL.
                </p>
              </div>

              {(!analyticsData?.topic_mastery || analyticsData.topic_mastery.length === 0) && progressData.length === 0 ? (
                <div className="status-placeholder">
                  No learning progress logged yet. Take a quiz or practice questions to start building your mastery profile!
                </div>
              ) : (
                <div className="mastery-grid">
                  {(analyticsData?.topic_mastery || progressData).map((item, idx) => {
                    const trendClass =
                      item.trend === 'improving'
                        ? 'trend-improving'
                        : item.trend === 'declining'
                        ? 'trend-declining'
                        : 'trend-stable';
                    const trendIcon = item.trend === 'improving' ? '↗️' : item.trend === 'declining' ? '↘️' : '➡️';

                    return (
                      <div key={idx} className="mastery-card">
                        <div className="mastery-header">
                          <div>
                            <h4 className="mastery-topic">{item.topic}</h4>
                            {item.subtopic && <div className="mastery-subtopic">{item.subtopic}</div>}
                          </div>
                          <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                            {item.trend && (
                              <span className={`trend-badge ${trendClass}`}>
                                {trendIcon} {item.trend.toUpperCase()}
                              </span>
                            )}
                            <span
                              className="badge"
                              style={{
                                background: item.status === 'mastered' ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)',
                                color: item.status === 'mastered' ? '#34d399' : '#fbbf24',
                                fontWeight: 700,
                              }}
                            >
                              {(item.status || 'in_progress').toUpperCase()}
                            </span>
                          </div>
                        </div>

                        <div className="mastery-meter-container">
                          <div className="mastery-meter-bar">
                            <div
                              className="mastery-meter-fill"
                              style={{
                                width: `${Math.min(100, Math.max(0, item.mastery_score))}%`,
                                background:
                                  item.mastery_score >= 80 ? '#10b981' : item.mastery_score >= 50 ? '#38bdf8' : '#f59e0b',
                              }}
                            ></div>
                          </div>
                          <div className="mastery-meter-label">
                            <span>{item.mastery_score}% Mastery</span>
                            <span>{item.correct_answers}/{item.total_questions} Correct</span>
                          </div>
                        </div>

                        {item.last_mistake_summary && (
                          <div className="mistake-box">
                            <span className="mistake-label">⚠️ Last Mistake Note:</span>
                            <span className="mistake-text">{item.last_mistake_summary}</span>
                          </div>
                        )}

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                            {item.attempts_count ? `${item.attempts_count} attempt(s)` : ''}
                          </span>
                          <button
                            type="button"
                            className="btn-rec-action"
                            style={{ padding: '0.35rem 0.7rem', fontSize: '0.78rem' }}
                            onClick={() => handleGenerateTargetedQuiz(item.topic)}
                            disabled={generatingTargeted && targetedTopic === item.topic}
                          >
                            🎯 Targeted Practice
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* 5. PROGRESS OVER TIME / ATTEMPTS TIMELINE */}
            <section className="card">
              <div className="qa-header">
                <div className="section-badge">⏱️ Attempt History</div>
                <h2 className="status-title" style={{ marginTop: '0.4rem' }}>
                  Progress Over Time & Quiz History
                </h2>
                <p className="status-description">
                  Chronological record of completed quizzes, scores, mastery feedback, and evaluation dates in Neon PostgreSQL.
                </p>
              </div>

              {(!analyticsData?.attempts_timeline || analyticsData.attempts_timeline.length === 0) && quizAttempts.length === 0 ? (
                <div className="status-placeholder">
                  No quiz attempts completed yet. Take a quiz to record your history!
                </div>
              ) : (
                <div className="timeline-container">
                  {(analyticsData?.attempts_timeline || quizAttempts).map((att) => {
                    const pct = Math.round(att.percentage);
                    const isSuccess = pct >= 80;
                    const isMedium = pct >= 50;

                    return (
                      <div key={att.id} className="timeline-card">
                        <div className="timeline-left">
                          <div
                            className="timeline-score"
                            style={{
                              background: isSuccess ? 'rgba(16,185,129,0.15)' : isMedium ? 'rgba(56,189,248,0.15)' : 'rgba(239,68,68,0.15)',
                              color: isSuccess ? '#34d399' : isMedium ? '#38bdf8' : '#f87171',
                              border: `1px solid ${isSuccess ? 'rgba(16,185,129,0.3)' : isMedium ? 'rgba(56,189,248,0.3)' : 'rgba(239,68,68,0.3)'}`,
                            }}
                          >
                            {pct}%
                          </div>
                          <div className="timeline-info">
                            <h4>{att.quiz_title || 'Quiz'}</h4>
                            <p>
                              {att.quiz_topic} &bull; {att.score}/{att.total_questions} Correct &bull;{' '}
                              {att.created_at ? new Date(att.created_at).toLocaleDateString() : 'Recent'} at{' '}
                              {att.created_at ? new Date(att.created_at).toLocaleTimeString() : ''}
                            </p>
                          </div>
                        </div>

                        {att.feedback && (
                          <div className="timeline-feedback">
                            "{att.feedback}"
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* 6. System Health Check Card */}
            <section className="card status-card">
              <div className="status-header">
                <div>
                  <h2 className="status-title">System & Database Connectivity</h2>
                  <p className="status-description">
                    Verify real-time communication between React, FastAPI, Neon PostgreSQL (pgvector), and Gemini.
                  </p>
                </div>
                <button
                  className="btn-primary"
                  onClick={checkBackendHealth}
                  disabled={healthLoading}
                >
                  {healthLoading ? (
                    <>
                      <span className="spinner"></span>
                      Checking...
                    </>
                  ) : (
                    'Refresh Health'
                  )}
                </button>
              </div>

              <div className="status-display">
                {healthStatus && (
                  <div className="status-grid">
                    <div className="alert alert-success">
                      <div className="alert-icon">✓</div>
                      <div className="alert-details">
                        <div className="alert-heading">FastAPI Backend: Online</div>
                        <div className="alert-meta">
                          Target: <code>{API_BASE_URL}/health</code> | Checked: {lastChecked}
                        </div>
                      </div>
                    </div>

                    <div className={`alert ${healthStatus.database?.connected ? 'alert-success' : 'alert-warning'}`}>
                      <div className="alert-icon">{healthStatus.database?.connected ? '✓' : '⚠️'}</div>
                      <div className="alert-details">
                        <div className="alert-heading">
                          Neon PostgreSQL: {healthStatus.database?.connected ? 'Connected' : 'Action Required'}
                        </div>
                        <div className="alert-body">
                          {healthStatus.database?.message || 'Status unknown'}
                        </div>
                      </div>
                    </div>

                    <div className={`alert ${healthStatus.gemini?.configured ? 'alert-success' : 'alert-warning'}`}>
                      <div className="alert-icon">{healthStatus.gemini?.configured ? '✓' : 'ℹ️'}</div>
                      <div className="alert-details">
                        <div className="alert-heading">
                          Gemini API ({healthStatus.gemini?.model}): {healthStatus.gemini?.configured ? 'Active' : 'Key Required'}
                        </div>
                        <div className="alert-body">
                          {healthStatus.gemini?.message || 'Status unknown'}
                        </div>
                      </div>
                    </div>

                    <div className="alert alert-success">
                      <div className="alert-icon">📚</div>
                      <div className="alert-details">
                        <div className="alert-heading">
                          Study Notes RAG & Quiz Engine: Ready
                        </div>
                        <div className="alert-body">
                          Embedding Model: <code>{healthStatus.rag?.embedding_model}</code> (768-dim) &bull; Indexed Documents: <strong>{healthStatus.rag?.documents_count}</strong> &bull; Vector Chunks: <strong>{healthStatus.rag?.chunks_count}</strong> &bull; Total Quizzes: <strong>{healthStatus.quizzes?.total_quizzes}</strong>
                        </div>
                      </div>
                    </div>

                    <pre className="payload-box">{JSON.stringify(healthStatus, null, 2)}</pre>
                  </div>
                )}

                {healthError && (
                  <div className="alert alert-error">
                    <div className="alert-icon">✕</div>
                    <div className="alert-details">
                      <div className="alert-heading">Connection Failed</div>
                      <div className="alert-body">{healthError}</div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </>
        )}

        {/* ======================================================== */}
        {/* TAB 4: MULTI-AGENT STUDY HUB                             */}
        {/* ======================================================== */}
        {activeTab === 'agents' && (
          <>
            {/* 1. AGENTS ORCHESTRATION HEADER & FLEET STATUS */}
            <section className="card">
              <div className="qa-header">
                <div className="section-badge">🤖 Central Orchestrator &bull; 5 Specialized Agents</div>
                <h2 className="status-title" style={{ marginTop: '0.4rem' }}>
                  Multi-Agent Adaptive Learning Hub
                </h2>
                <p className="status-description">
                  Specialized AI agents continuously collaborate to analyze your performance, synthesize adaptive study plans, ground recommendations in your notes, and update your concept mastery.
                </p>
              </div>

              {agentActionMessage && (
                <div className="alert alert-success" style={{ marginTop: '1rem' }}>
                  <div className="alert-icon">✓</div>
                  <div className="alert-details">
                    <div className="alert-heading">Multi-Agent Action Succeeded</div>
                    <div className="alert-body">{agentActionMessage}</div>
                  </div>
                </div>
              )}

              {/* 5-Agent Fleet Cards Grid */}
              <div className="agent-fleet-grid">
                {/* 1. Learner Profiling Agent */}
                <div className="agent-card">
                  <div>
                    <div className="agent-card-header">
                      <div className="agent-icon-badge">🧠</div>
                      <span className="agent-status-pill">
                        <span className="agent-pulse-dot"></span>
                        {agentStatus?.agents?.learner_profiler?.status || 'READY'}
                      </span>
                    </div>
                    <div className="agent-card-title">Learner Profiling Agent</div>
                    <div className="agent-card-desc">
                      Diagnoses quiz answers, identifies misconception patterns, calculates learning velocity, and assigns mastery tiers.
                    </div>
                  </div>
                  <div className="agent-card-footer">
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                      Tier: {learnerProfile?.learning_tier || 'Developing'}
                    </span>
                    <span style={{ color: '#9ca3af' }}>
                      {learnerProfile?.overall_accuracy ?? 0}% Acc
                    </span>
                  </div>
                </div>

                {/* 2. Curriculum Planner Agent */}
                <div className="agent-card">
                  <div>
                    <div className="agent-card-header">
                      <div className="agent-icon-badge">🗺️</div>
                      <span className="agent-status-pill">
                        <span className="agent-pulse-dot"></span>
                        {agentStatus?.agents?.curriculum_planner?.status || 'READY'}
                      </span>
                    </div>
                    <div className="agent-card-title">Curriculum Planner Agent</div>
                    <div className="agent-card-desc">
                      Synthesizes a 3-phase adaptive curriculum: Remediation &rarr; Core Expansion &rarr; Placement Readiness.
                    </div>
                  </div>
                  <div className="agent-card-footer">
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                      {studyPlan ? 'Plan Active' : 'Ready'}
                    </span>
                    <span style={{ color: '#9ca3af' }}>
                      {studyPlan?.target_timeline || '2 Weeks'}
                    </span>
                  </div>
                </div>

                {/* 3. Content Recommendation Agent */}
                <div className="agent-card">
                  <div>
                    <div className="agent-card-header">
                      <div className="agent-icon-badge">📚</div>
                      <span className="agent-status-pill">
                        <span className="agent-pulse-dot"></span>
                        {agentStatus?.agents?.content_recommender?.status || 'READY'}
                      </span>
                    </div>
                    <div className="agent-card-title">Content Recommendation Agent</div>
                    <div className="agent-card-desc">
                      Matches specific weak concepts and curriculum goals to excerpts in your uploaded notes via Neon pgvector similarity search.
                    </div>
                  </div>
                  <div className="agent-card-footer">
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                      Grounded pgvector
                    </span>
                    <span style={{ color: '#9ca3af' }}>
                      {healthStatus?.rag?.documents_count ?? 8} Notes
                    </span>
                  </div>
                </div>

                {/* 4. Quiz Agent */}
                <div className="agent-card">
                  <div>
                    <div className="agent-card-header">
                      <div className="agent-icon-badge">⚡</div>
                      <span className="agent-status-pill">
                        <span className="agent-pulse-dot"></span>
                        {agentStatus?.agents?.quiz_agent?.status || 'READY'}
                      </span>
                    </div>
                    <div className="agent-card-title">Quiz Agent</div>
                    <div className="agent-card-desc">
                      Generates targeted 4-option remediation MCQs and milestone assessments grounded in note context.
                    </div>
                  </div>
                  <div className="agent-card-footer">
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                      Targeted Practice
                    </span>
                    <span style={{ color: '#9ca3af' }}>
                      4-Option MCQs
                    </span>
                  </div>
                </div>

                {/* 5. Evaluation Agent */}
                <div className="agent-card">
                  <div>
                    <div className="agent-card-header">
                      <div className="agent-icon-badge">🎓</div>
                      <span className="agent-status-pill">
                        <span className="agent-pulse-dot"></span>
                        {agentStatus?.agents?.evaluation_agent?.status || 'READY'}
                      </span>
                    </div>
                    <div className="agent-card-title">Evaluation Agent</div>
                    <div className="agent-card-desc">
                      Evaluates answers, separates mastered concepts from knowledge gaps, and advances study plan milestones.
                    </div>
                  </div>
                  <div className="agent-card-footer">
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                      Gap Analysis
                    </span>
                    <span style={{ color: '#9ca3af' }}>
                      Auto-Mastery
                    </span>
                  </div>
                </div>
              </div>
            </section>

            {/* 2. LEARNER PROFILING AGENT DIAGNOSTIC CARD */}
            <section className="card">
              <div className="qa-header">
                <div className="section-badge">🧠 Learner Intelligence & Cognitive Diagnosis</div>
                <h3 className="status-title" style={{ marginTop: '0.4rem' }}>
                  Learner Profile & Misconception Analysis
                </h3>
                <p className="status-description">
                  Real-time cognitive profile generated by the Learner Profiling Agent from your Neon PostgreSQL performance history.
                </p>
              </div>

              <div className="learner-profile-grid">
                <div className="profile-stat-box">
                  <div className="profile-stat-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
                    🎯
                  </div>
                  <div>
                    <div className="profile-stat-value">{learnerProfile?.overall_accuracy ?? 0}%</div>
                    <div className="profile-stat-label">Overall Accuracy</div>
                  </div>
                </div>

                <div className="profile-stat-box">
                  <div className="profile-stat-icon" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
                    🚀
                  </div>
                  <div>
                    <div className="profile-stat-value" style={{ fontSize: '1.05rem', color: '#7dd3fc' }}>
                      {learnerProfile?.learning_velocity || 'Analyzing'}
                    </div>
                    <div className="profile-stat-label">Learning Velocity</div>
                  </div>
                </div>

                <div className="profile-stat-box">
                  <div className="profile-stat-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
                    🏆
                  </div>
                  <div>
                    <div className="profile-stat-value" style={{ fontSize: '1.15rem', color: '#34d399' }}>
                      {learnerProfile?.learning_tier || 'Developing'}
                    </div>
                    <div className="profile-stat-label">Current Mastery Tier</div>
                  </div>
                </div>

                <div className="profile-stat-box">
                  <div className="profile-stat-icon" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>
                    📝
                  </div>
                  <div>
                    <div className="profile-stat-value">
                      {learnerProfile?.total_questions_answered ?? 0}
                    </div>
                    <div className="profile-stat-label">
                      Questions ({learnerProfile?.total_quizzes_taken ?? 0} Quizzes)
                    </div>
                  </div>
                </div>
              </div>

              {/* Pedagogical Narrative Callout */}
              {learnerProfile?.summary_narrative && (
                <div className="profile-narrative-card">
                  <div className="profile-narrative-avatar">🧠</div>
                  <div>
                    <div style={{ fontSize: '0.8rem', color: '#a5b4fc', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                      Profiling Agent Pedagogical Narrative
                    </div>
                    <div className="profile-narrative-text">
                      "{learnerProfile.summary_narrative}"
                    </div>
                  </div>
                </div>
              )}

              {/* Mastered & Weak Topics Breakdown */}
              <div className="profile-topics-row">
                <div className="profile-topic-section">
                  <div className="profile-topic-heading">
                    <span style={{ color: '#34d399' }}>✓</span> Mastered Knowledge Areas ({learnerProfile?.mastered_topics?.length || 0})
                  </div>
                  {(!learnerProfile?.mastered_topics || learnerProfile.mastered_topics.length === 0) ? (
                    <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>No topics at &gt;=80% mastery yet. Keep practicing!</div>
                  ) : (
                    <div className="profile-chip-list">
                      {learnerProfile.mastered_topics.map((t, idx) => (
                        <span key={idx} className="profile-chip profile-chip-mastered">
                          ✓ {t.topic} ({Math.round(t.mastery_score)}%)
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="profile-topic-section">
                  <div className="profile-topic-heading">
                    <span style={{ color: '#f87171' }}>⚠️</span> Priority Weak Topics Requiring Remediation ({learnerProfile?.weak_topics?.length || 0})
                  </div>
                  {(!learnerProfile?.weak_topics || learnerProfile.weak_topics.length === 0) ? (
                    <div style={{ fontSize: '0.8rem', color: '#34d399' }}>All quizzed topics currently above 75% mastery!</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                      {learnerProfile.weak_topics.map((wt, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: 'rgba(239, 68, 68, 0.08)',
                            border: '1px solid rgba(239, 68, 68, 0.25)',
                            borderRadius: '8px',
                            padding: '0.65rem 0.85rem',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '0.5rem',
                          }}
                        >
                          <div>
                            <div style={{ fontWeight: 700, color: '#fca5a5', fontSize: '0.85rem' }}>
                              {wt.topic} &bull; {Math.round(wt.mastery_score)}% Mastery
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.15rem' }}>
                              {wt.mistake_count} mistake(s) logged
                              {wt.missed_concepts && wt.missed_concepts.length > 0 && ` &bull; Focus: ${wt.missed_concepts[0].slice(0, 45)}...`}
                            </div>
                          </div>
                          <button
                            type="button"
                            className="btn-practice-targeted"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                            onClick={() => handleRemediateWeakTopic(wt.topic)}
                            disabled={remediatingTopic === wt.topic}
                          >
                            {remediatingTopic === wt.topic ? (
                              <>
                                <span className="spinner"></span>
                                Generating...
                              </>
                            ) : (
                              '🎯 Remediate Now'
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </section>

            {/* 3. CURRICULUM PLANNER AGENT: ADAPTIVE STUDY PLAN */}
            <section className="card">
              <div className="qa-header">
                <div className="section-badge">🗺️ Curriculum Planner Agent</div>
                <h3 className="status-title" style={{ marginTop: '0.4rem' }}>
                  Personalized Adaptive Study Plan
                </h3>
                <p className="status-description">
                  The Curriculum Planner synthesizes a phased roadmap tailored to your specific timeline, weak concepts, and study notes.
                </p>
              </div>

              {/* Study Plan Synthesizer Form */}
              <form onSubmit={handleGenerateStudyPlan} className="quiz-generator-form" style={{ marginTop: '1rem' }}>
                <div className="quiz-setup-grid">
                  <div className="form-row">
                    <label className="form-label" htmlFor="plan-goal-input">
                      Your Primary Learning Goal / Target Objective:
                    </label>
                    <input
                      id="plan-goal-input"
                      type="text"
                      className="text-input"
                      value={studyPlanGoal}
                      onChange={(e) => setStudyPlanGoal(e.target.value)}
                      placeholder="e.g. Core Computer Science Placement & Tech Interview Mastery"
                      required
                    />
                    <div className="preset-row" style={{ marginTop: '0.4rem' }}>
                      <span className="preset-label">Goal Presets:</span>
                      {[
                        'Core Computer Science Placement & Tech Interview Mastery',
                        'OS Concurrency, Deadlocks & Virtual Memory',
                        'DSA Problem Solving & Graph Algorithms',
                        'Database Indexing, Transactions & SQL Mastery',
                      ].map((preset, pIdx) => (
                        <button
                          key={pIdx}
                          type="button"
                          className="preset-btn"
                          onClick={() => setStudyPlanGoal(preset)}
                        >
                          {preset.split(' ')[0]}...
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="form-row-split">
                    <div className="form-row" style={{ flex: 1 }}>
                      <label className="form-label" htmlFor="plan-timeline-select">
                        Target Timeline:
                      </label>
                      <select
                        id="plan-timeline-select"
                        className="select-input"
                        value={studyPlanTimeline}
                        onChange={(e) => setStudyPlanTimeline(e.target.value)}
                      >
                        <option value="1 Week">1 Week (Sprint Intensive)</option>
                        <option value="2 Weeks">2 Weeks (Balanced Mastery)</option>
                        <option value="1 Month">1 Month (Comprehensive)</option>
                      </select>
                    </div>

                    <div className="form-row" style={{ flex: 2 }}>
                      <label className="form-label">Focus Subject Domains:</label>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.35rem' }}>
                        {PRESET_TOPICS.filter((t) => t !== 'General').map((topic) => {
                          const isChecked = studyPlanFocusTopics.includes(topic);
                          return (
                            <label
                              key={topic}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                fontSize: '0.78rem',
                                color: isChecked ? '#38bdf8' : '#9ca3af',
                                background: isChecked ? 'rgba(56, 189, 248, 0.12)' : 'rgba(255, 255, 255, 0.04)',
                                border: `1px solid ${isChecked ? 'rgba(56, 189, 248, 0.3)' : 'rgba(255, 255, 255, 0.08)'}`,
                                padding: '0.25rem 0.55rem',
                                borderRadius: '6px',
                                cursor: 'pointer',
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setStudyPlanFocusTopics([...studyPlanFocusTopics, topic]);
                                  } else {
                                    setStudyPlanFocusTopics(studyPlanFocusTopics.filter((t) => t !== topic));
                                  }
                                }}
                              />
                              {topic}
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="form-actions" style={{ marginTop: '1.25rem' }}>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={generatingPlan || !studyPlanGoal.trim()}
                  >
                    {generatingPlan ? (
                      <>
                        <span className="spinner"></span>
                        Curriculum Planner Agent is orchestrating study plan...
                      </>
                    ) : (
                      'Synthesize Adaptive Study Plan 🚀'
                    )}
                  </button>
                </div>
              </form>

              {/* ACTIVE STUDY PLAN DISPLAY */}
              {studyPlan && (
                <div className="study-plan-card">
                  <div className="plan-header-banner">
                    <div>
                      <div className="plan-title-big">{studyPlan.title}</div>
                      <div className="plan-goal-line">
                        <strong>Goal:</strong> {studyPlan.goal} &bull; <strong>Target:</strong> {studyPlan.target_timeline}
                      </div>
                    </div>
                    <span
                      className="badge"
                      style={{
                        background: 'rgba(16, 185, 129, 0.2)',
                        color: '#34d399',
                        borderColor: 'rgba(16, 185, 129, 0.4)',
                        fontWeight: 700,
                        fontSize: '0.82rem',
                      }}
                    >
                      ✓ ACTIVE CURRICULUM
                    </span>
                  </div>

                  {/* Overall Plan Milestone Completion Progress Bar */}
                  {(() => {
                    const allMilestones = (studyPlan.phases || []).flatMap((p) => p.milestones || []);
                    const totalMilestones = allMilestones.length;
                    const completedMilestones = allMilestones.filter((m) => m.status === 'completed').length;
                    const progressPercent = totalMilestones > 0 ? Math.round((completedMilestones / totalMilestones) * 100) : 0;

                    return (
                      <div className="plan-progress-wrapper">
                        <div className="plan-progress-header">
                          <span>Curriculum Progress: {completedMilestones} of {totalMilestones} Milestones Completed</span>
                          <span style={{ color: '#34d399', fontWeight: 700 }}>{progressPercent}% Complete</span>
                        </div>
                        <div className="plan-progress-track">
                          <div className="plan-progress-fill" style={{ width: `${progressPercent}%` }}></div>
                        </div>
                      </div>
                    );
                  })()}

                  {/* 3-PHASE ADAPTIVE CURRICULUM CONTAINER */}
                  <div className="phases-container">
                    {(studyPlan.phases || []).map((phase, pIdx) => (
                      <div key={pIdx} className="phase-block">
                        <div className="phase-header-bar">
                          <span className="phase-name-tag">
                            <span>📌</span> {phase.phase_name}
                          </span>
                          <span className="phase-focus-tag">
                            <strong>Focus:</strong> {phase.focus}
                          </span>
                        </div>

                        <div className="milestones-list">
                          {(phase.milestones || []).map((milestone) => {
                            const isCompleted = milestone.status === 'completed';
                            const isInProgress = milestone.status === 'in_progress';

                            return (
                              <div
                                key={milestone.id}
                                className={`milestone-item ${isCompleted ? 'is-completed' : isInProgress ? 'is-in-progress' : ''}`}
                              >
                                <div className="milestone-left">
                                  <div className="milestone-status-icon">
                                    {isCompleted ? '✅' : isInProgress ? '⏳' : '⚪'}
                                  </div>
                                  <div>
                                    <div className="milestone-title-text">{milestone.title}</div>
                                    <div className="milestone-meta-row">
                                      <span className="badge badge-version">{milestone.topic}</span>
                                      <span className="badge badge-phase">
                                        {(milestone.action_type || 'practice').replace('_', ' ')}
                                      </span>
                                      <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                                        ⏱️ ~{milestone.estimated_minutes} min
                                      </span>
                                      <span
                                        className="badge"
                                        style={{
                                          background: isCompleted
                                            ? 'rgba(16, 185, 129, 0.2)'
                                            : isInProgress
                                            ? 'rgba(56, 189, 248, 0.2)'
                                            : 'rgba(255, 255, 255, 0.08)',
                                          color: isCompleted ? '#34d399' : isInProgress ? '#7dd3fc' : '#9ca3af',
                                        }}
                                      >
                                        {(milestone.status || 'pending').toUpperCase()}
                                      </span>
                                    </div>
                                  </div>
                                </div>

                                <div className="milestone-actions-right">
                                  {/* Direct Milestone Action */}
                                  <button
                                    type="button"
                                    className="btn-milestone-practice"
                                    onClick={() => handleStartMilestonePractice(milestone)}
                                    disabled={remediatingTopic === milestone.topic}
                                  >
                                    {remediatingTopic === milestone.topic ? (
                                      <>
                                        <span className="spinner"></span>
                                        Starting...
                                      </>
                                    ) : (
                                      <>
                                        <span>🎯</span> Start Milestone Practice
                                      </>
                                    )}
                                  </button>

                                  {/* Status manual toggle */}
                                  <select
                                    className="select-milestone-status"
                                    value={milestone.status || 'pending'}
                                    onChange={(e) => handleUpdateMilestoneStatus(milestone.id, e.target.value)}
                                  >
                                    <option value="pending">Pending</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="completed">Completed</option>
                                  </select>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Collaborative Agent Trace Accordion */}
                  {studyPlan.agent_trace && (
                    <div className="agent-trace-wrapper">
                      <div
                        className="agent-trace-header"
                        onClick={() => setExpandedTrace(!expandedTrace)}
                      >
                        <span>🤖 Collaborative Agent Execution Trace ({studyPlan.agent_trace.steps?.length || 0} Steps)</span>
                        <span>{expandedTrace ? '▲ Hide Trace' : '▼ View Trace'}</span>
                      </div>

                      {expandedTrace && (
                        <div className="agent-trace-list">
                          {(studyPlan.agent_trace.steps || []).map((step, sIdx) => (
                            <div key={sIdx} className="agent-trace-step">
                              <div>
                                <span className="agent-trace-agent-tag">[{step.agent}]</span>{' '}
                                <strong style={{ color: '#f3f4f6' }}>{step.action}</strong>
                              </div>
                              <div className="agent-trace-summary">{step.summary}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* 4. CONTENT RECOMMENDATION AGENT: GROUNDED NOTES SHELF */}
            {studyPlan?.content_recommendations && studyPlan.content_recommendations.length > 0 && (
              <section className="card">
                <div className="qa-header">
                  <div className="section-badge">📚 Content Recommendation Agent &bull; pgvector Grounded</div>
                  <h3 className="status-title" style={{ marginTop: '0.4rem' }}>
                    Recommended Study Excerpts for Misconception Repair
                  </h3>
                  <p className="status-description">
                    Matched using 768-dim vector embeddings directly against your uploaded lecture notes and study PDFs.
                  </p>
                </div>

                <div className="rec-shelf-grid">
                  {studyPlan.content_recommendations.map((rec, rIdx) => (
                    <div key={rIdx} className="rec-shelf-card">
                      <div>
                        <div className="rec-shelf-title">
                          <span>📑</span> {rec.document_title || 'Study Notes'}
                          {rec.page_number && (
                            <span className="badge badge-version" style={{ fontSize: '0.7rem' }}>
                              Page {rec.page_number}
                            </span>
                          )}
                        </div>
                        <div className="rec-shelf-rationale">
                          🎯 {rec.rationale}
                        </div>
                        <div className="rec-shelf-excerpt">
                          "{rec.excerpt || rec.content}"
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem', width: '100%', justifyContent: 'center' }}
                        onClick={() => handleAskAboutNote(rec)}
                      >
                        🔍 Ask Notes (RAG) About This Concept
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {/* ======================================================== */}
        {/* TAB 5: DSA HEATMAP & PROBLEM TRACKER                    */}
        {/* ======================================================== */}
        {activeTab === 'dsa' && (
          <>
            {/* 1. HERO STATS & STREAK CARDS */}
            <div className="dsa-hero-stats">
              <div className="dsa-stat-card">
                <span style={{ fontSize: '1.8rem' }}>🎯</span>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Solved</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc' }}>
                    {dsaHeatmap?.total_problems ?? 0}
                  </div>
                </div>
              </div>

              <div className="dsa-stat-card">
                <span className="dsa-streak-fire" style={{ fontSize: '1.8rem' }}>🔥</span>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Current Streak</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f59e0b' }}>
                    {dsaHeatmap?.current_streak ?? 0} <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>days</span>
                  </div>
                </div>
              </div>

              <div className="dsa-stat-card">
                <span style={{ fontSize: '1.8rem' }}>⚡</span>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Max Streak</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#10b981' }}>
                    {dsaHeatmap?.max_streak ?? 0} <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>days</span>
                  </div>
                </div>
              </div>

              <div className="dsa-stat-card">
                <span style={{ fontSize: '1.8rem' }}>📅</span>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Active Days</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#38bdf8' }}>
                    {dsaHeatmap?.active_days_count ?? 0} <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>/ 365</span>
                  </div>
                </div>
              </div>

              <div className="dsa-stat-card" style={{ flexWrap: 'wrap', gap: '0.4rem' }}>
                <span className="badge badge-easy" style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
                  Easy: {dsaHeatmap?.difficulty_breakdown?.Easy ?? 0}
                </span>
                <span className="badge badge-medium" style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
                  Medium: {dsaHeatmap?.difficulty_breakdown?.Medium ?? 0}
                </span>
                <span className="badge badge-hard" style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
                  Hard: {dsaHeatmap?.difficulty_breakdown?.Hard ?? 0}
                </span>
              </div>
            </div>

            {/* 2. 52-WEEK LEETCODE/GITHUB GREEN HEATMAP CARD */}
            <section className="card heatmap-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
                <div>
                  <div className="section-badge">🟩 Neon PostgreSQL &bull; Activity Matrix</div>
                  <h3 className="status-title" style={{ marginTop: '0.35rem' }}>
                    {dsaHeatmap?.total_problems ?? 0} Problems Solved in the Past Year
                  </h3>
                  <p className="status-description">
                    Live daily LeetCode/DSA activity tracked in Neon PostgreSQL. Hover over any cell to inspect date and problem count.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setDsaModalOpen(true)}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <span>+</span> Log Solved Problem
                </button>
              </div>

              {dsaLoading ? (
                <div style={{ textAlign: 'center', padding: '2.5rem', color: '#94a3b8' }}>
                  Loading activity heatmap from Neon...
                </div>
              ) : (
                <div className="heatmap-scroll-wrapper">
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                    {/* Day of week labels */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.65rem', color: '#64748b', fontWeight: 600, paddingRight: '4px', userSelect: 'none' }}>
                      <div style={{ height: '13px', lineHeight: '13px' }}>Mon</div>
                      <div style={{ height: '13px', lineHeight: '13px' }}></div>
                      <div style={{ height: '13px', lineHeight: '13px' }}>Wed</div>
                      <div style={{ height: '13px', lineHeight: '13px' }}></div>
                      <div style={{ height: '13px', lineHeight: '13px' }}>Fri</div>
                      <div style={{ height: '13px', lineHeight: '13px' }}></div>
                      <div style={{ height: '13px', lineHeight: '13px' }}>Sun</div>
                    </div>

                    {/* Columns of 7 days */}
                    <div className="heatmap-matrix">
                      {groupHeatmapDaysIntoWeeks(dsaHeatmap?.days || []).map((week, wIdx) => (
                        <div key={wIdx} className="heatmap-week-col">
                          {week.map((day, dIdx) => {
                            if (!day) {
                              return <div key={dIdx} style={{ width: '13px', height: '13px' }} />;
                            }
                            return (
                              <div
                                key={dIdx}
                                className={`heatmap-cell cell-level-${day.intensity}`}
                                onMouseEnter={() => setDsaHoveredDay(day)}
                                onMouseLeave={() => setDsaHoveredDay(null)}
                                onClick={() => {
                                  setDsaForm(prev => ({ ...prev, activity_date: day.date }));
                                  setDsaModalOpen(true);
                                }}
                                title={`${day.problem_count} problem(s) on ${day.date}`}
                              />
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Footer & Legend */}
                  <div className="heatmap-footer-bar">
                    <div style={{ color: '#cbd5e1', fontWeight: 500 }}>
                      {dsaHoveredDay ? (
                        <span>
                          <strong>{dsaHoveredDay.problem_count}</strong> {dsaHoveredDay.problem_count === 1 ? 'problem' : 'problems'} on <strong>{dsaHoveredDay.date}</strong>
                        </span>
                      ) : (
                        <span>Click any square to log a problem for that date</span>
                      )}
                    </div>
                    <div className="heatmap-legend-row">
                      <span>Less</span>
                      <div className="heatmap-cell cell-level-0" style={{ cursor: 'default' }} />
                      <div className="heatmap-cell cell-level-1" style={{ cursor: 'default' }} />
                      <div className="heatmap-cell cell-level-2" style={{ cursor: 'default' }} />
                      <div className="heatmap-cell cell-level-3" style={{ cursor: 'default' }} />
                      <div className="heatmap-cell cell-level-4" style={{ cursor: 'default' }} />
                      <span>More</span>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* 3. RECENT PROBLEMS FEED */}
            <section className="card" style={{ marginTop: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div className="section-badge">📝 Solved Problems Activity Feed</div>
                  <h3 className="status-title" style={{ marginTop: '0.35rem' }}>
                    Recent Submissions ({dsaHeatmap?.recent_problems?.length || 0})
                  </h3>
                </div>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => fetchDsaHeatmap(activeUserId)}
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                >
                  🔄 Refresh
                </button>
              </div>

              {(!dsaHeatmap?.recent_problems || dsaHeatmap.recent_problems.length === 0) ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                  No problems logged yet. Click <strong>"+ Log Solved Problem"</strong> to record your first LeetCode/DSA problem!
                </div>
              ) : (
                <div className="dsa-problem-feed">
                  {dsaHeatmap.recent_problems.map((prob) => {
                    const diffBadgeClass = prob.difficulty === 'Easy' ? 'badge-easy' : prob.difficulty === 'Hard' ? 'badge-hard' : 'badge-medium';
                    return (
                      <div key={prob.id} className="dsa-problem-row">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '1.2rem' }}>
                            {prob.platform === 'LeetCode' ? '🟧' : prob.platform === 'Codeforces' ? '🔷' : prob.platform === 'GeeksforGeeks' ? '🟩' : '💻'}
                          </span>
                          <div>
                            <div style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.95rem' }}>
                              {prob.problem_url ? (
                                <a href={prob.problem_url} target="_blank" rel="noopener noreferrer" style={{ color: '#38bdf8', textDecoration: 'none' }}>
                                  {prob.problem_title} ↗
                                </a>
                              ) : (
                                prob.problem_title
                              )}
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.25rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                              <span className={`badge ${diffBadgeClass}`} style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem' }}>
                                {prob.difficulty}
                              </span>
                              <span className="badge" style={{ background: '#1e293b', color: '#cbd5e1', fontSize: '0.7rem' }}>
                                {prob.platform}
                              </span>
                              <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', fontSize: '0.7rem' }}>
                                {prob.topic}
                              </span>
                              <span>📅 {prob.activity_date}</span>
                            </div>
                            {prob.notes && (
                              <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.35rem', fontStyle: 'italic', background: 'rgba(0,0,0,0.2)', padding: '0.3rem 0.6rem', borderRadius: '4px' }}>
                                💡 {prob.notes}
                              </div>
                            )}
                          </div>
                        </div>
                        <button
                          type="button"
                          className="btn-danger"
                          style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
                          onClick={() => handleDeleteDsaProblem(prob.id)}
                          title="Delete problem"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </>
        )}

        {/* ======================================================== */}
        {/* TAB 6: STUDY CALENDAR & TASK SCHEDULER                  */}
        {/* ======================================================== */}
        {activeTab === 'calendar' && (
          <>
            {/* 1. CALENDAR TOP NAVIGATION & CONTROLS */}
            <section className="card">
              <div className="calendar-top-bar">
                <div>
                  <div className="section-badge">📅 Interactive Study Planner</div>
                  <h3 className="status-title" style={{ marginTop: '0.35rem' }}>
                    Personalized Study Calendar
                  </h3>
                  <p className="status-description">
                    Plan revisions, schedule DSA practice, track milestones, and prioritize your preparation directly in Neon PostgreSQL.
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <div className="calendar-nav-controls">
                    <button type="button" className="btn-cal-nav" onClick={handlePrevMonth}>
                      &larr; Prev
                    </button>
                    <div className="calendar-month-title">
                      {calendarDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                    </div>
                    <button type="button" className="btn-cal-nav" onClick={handleNextMonth}>
                      Next &rarr;
                    </button>
                    <button type="button" className="btn-cal-nav" onClick={handleTodayMonth} style={{ marginLeft: '0.25rem' }}>
                      Today
                    </button>
                  </div>

                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => handleOpenCreateTask()}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                  >
                    <span>+</span> Schedule Task
                  </button>
                </div>
              </div>

              {/* Monthly Progress / Summary Banner */}
              <div className="cal-summary-banner">
                <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Total Tasks: </span>
                    <strong style={{ color: '#f8fafc' }}>{calendarSummary?.total_tasks ?? 0}</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Completed: </span>
                    <strong style={{ color: '#10b981' }}>{calendarSummary?.completed_tasks ?? 0}</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Pending: </span>
                    <strong style={{ color: '#f59e0b' }}>{calendarSummary?.pending_tasks ?? 0}</strong>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: '220px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 600 }}>
                    {calendarSummary?.completion_rate ?? 0}% Complete
                  </span>
                  <div style={{ flex: 1, height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${calendarSummary?.completion_rate ?? 0}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #10b981, #38bdf8)',
                        transition: 'width 0.4s ease',
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Filters Bar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>Category:</span>
                  {['all', 'DSA', 'Core CS', 'System Design', 'Revision', 'Project'].map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      className={`badge ${calendarCategoryFilter === cat ? 'badge-version' : ''}`}
                      style={{
                        cursor: 'pointer',
                        background: calendarCategoryFilter === cat ? '#6366f1' : '#1e293b',
                        color: calendarCategoryFilter === cat ? '#ffffff' : '#94a3b8',
                        border: '1px solid rgba(255,255,255,0.1)',
                      }}
                      onClick={() => setCalendarCategoryFilter(cat)}
                    >
                      {cat.toUpperCase()}
                    </button>
                  ))}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>Status:</span>
                  {['all', 'pending', 'completed'].map((st) => (
                    <button
                      key={st}
                      type="button"
                      className="badge"
                      style={{
                        cursor: 'pointer',
                        background: calendarStatusFilter === st ? '#3b82f6' : '#1e293b',
                        color: calendarStatusFilter === st ? '#ffffff' : '#94a3b8',
                        border: '1px solid rgba(255,255,255,0.1)',
                      }}
                      onClick={() => setCalendarStatusFilter(st)}
                    >
                      {st.charAt(0).toUpperCase() + st.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* 2. CALENDAR 7-COLUMN MONTH GRID */}
              <div className="calendar-grid-container">
                <div className="calendar-weekdays-row">
                  <div>Mon</div>
                  <div>Tue</div>
                  <div>Wed</div>
                  <div>Thu</div>
                  <div>Fri</div>
                  <div>Sat</div>
                  <div>Sun</div>
                </div>

                {calendarLoading ? (
                  <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                    Loading monthly tasks...
                  </div>
                ) : (
                  <div className="calendar-days-matrix">
                    {generateMonthMatrix(calendarDate).map((cell, idx) => {
                      const dayTasks = calendarTasks.filter((t) => {
                        if (t.task_date !== cell.dateStr) return false;
                        if (calendarCategoryFilter !== 'all' && t.category !== calendarCategoryFilter) return false;
                        if (calendarStatusFilter === 'completed' && !t.is_completed) return false;
                        if (calendarStatusFilter === 'pending' && t.is_completed) return false;
                        return true;
                      });

                      return (
                        <div
                          key={idx}
                          className={`calendar-day-box ${cell.isToday ? 'is-today' : ''} ${!cell.isCurrentMonth ? 'is-outside' : ''}`}
                          onClick={(e) => {
                            if (e.target.closest('.cal-task-pill') || e.target.closest('button')) return;
                            handleOpenCreateTask(cell.dateStr);
                          }}
                          title="Click to add task on this day"
                        >
                          <div className="day-header-number">
                            <span className="day-number-badge">{cell.dayNum}</span>
                            {dayTasks.length > 0 && (
                              <span style={{ fontSize: '0.65rem', color: '#94a3b8', fontWeight: 600 }}>
                                {dayTasks.filter(t => t.is_completed).length}/{dayTasks.length}
                              </span>
                            )}
                          </div>

                          <div className="calendar-task-list">
                            {dayTasks.map((task) => {
                              const catClass = task.category === 'DSA'
                                ? 'border-cat-dsa'
                                : task.category === 'Core CS'
                                ? 'border-cat-os'
                                : task.category === 'System Design'
                                ? 'border-cat-dbms'
                                : task.category === 'Revision'
                                ? 'border-cat-ai'
                                : 'border-cat-general';

                              const priorityDotClass = task.priority === 'high'
                                ? 'priority-dot-high'
                                : task.priority === 'low'
                                ? 'priority-dot-low'
                                : 'priority-dot-medium';

                              return (
                                <div
                                  key={task.id}
                                  className={`cal-task-pill ${catClass} ${task.is_completed ? 'is-done' : ''}`}
                                  onClick={() => handleOpenEditTask(task)}
                                  title={`${task.title} (${task.category}) - Priority: ${task.priority}${task.start_time ? ` | ${task.start_time}` : ''}`}
                                >
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', overflow: 'hidden' }}>
                                    <input
                                      type="checkbox"
                                      checked={task.is_completed}
                                      onChange={(e) => {
                                        e.stopPropagation();
                                        handleToggleTask(task.id);
                                      }}
                                      style={{ cursor: 'pointer', accentColor: '#10b981' }}
                                    />
                                    <div className={priorityDotClass} />
                                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '85px' }}>
                                      {task.title}
                                    </span>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeleteTask(task.id);
                                    }}
                                    style={{
                                      background: 'transparent',
                                      border: 'none',
                                      color: '#ef4444',
                                      cursor: 'pointer',
                                      padding: '0 2px',
                                      fontSize: '0.7rem',
                                      opacity: 0.6,
                                    }}
                                    title="Delete task"
                                  >
                                    &times;
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </main>

      {/* ======================================================== */}
      {/* MODAL 1: AUTHENTICATION DIALOG (SIGN IN / SIGN UP)       */}
      {/* ======================================================== */}
      {authModalOpen && (
        <div className="auth-modal-overlay" onClick={() => setAuthModalOpen(false)}>
          <div className="auth-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="auth-modal-header">
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc', fontWeight: 800 }}>
                {authMode === 'signup' ? 'Create CloudLearn Account' : 'Sign In to CloudLearn AI'}
              </h3>
              <button
                type="button"
                onClick={() => setAuthModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            <div className="auth-tabs-toggle">
              <button
                type="button"
                className={`auth-tab-btn ${authMode === 'login' ? 'active' : ''}`}
                onClick={() => { setAuthMode('login'); setAuthError(null); }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth-tab-btn ${authMode === 'signup' ? 'active' : ''}`}
                onClick={() => { setAuthMode('signup'); setAuthError(null); }}
              >
                Sign Up
              </button>
            </div>

            <form onSubmit={handleAuthSubmit} className="auth-form-body">
              {authError && (
                <div className="alert alert-error" style={{ fontSize: '0.8rem', padding: '0.6rem 0.8rem' }}>
                  {authError}
                </div>
              )}

              {authMode === 'signup' && (
                <div className="form-row">
                  <label className="form-label">Full Name:</label>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="e.g. Alex Johnson"
                    value={authForm.full_name}
                    onChange={(e) => setAuthForm({ ...authForm, full_name: e.target.value })}
                  />
                </div>
              )}

              <div className="form-row">
                <label className="form-label">Username:</label>
                <input
                  type="text"
                  className="text-input"
                  placeholder="e.g. alex_coder"
                  value={authForm.username}
                  onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                  required
                />
              </div>

              {authMode === 'signup' && (
                <div className="form-row">
                  <label className="form-label">Email Address:</label>
                  <input
                    type="email"
                    className="text-input"
                    placeholder="e.g. alex@university.edu"
                    value={authForm.email}
                    onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                    required
                  />
                </div>
              )}

              <div className="form-row">
                <label className="form-label">Password:</label>
                <input
                  type="password"
                  className="text-input"
                  placeholder="At least 6 characters"
                  value={authForm.password}
                  onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn-primary"
                disabled={authLoading}
                style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem' }}
              >
                {authLoading ? 'Authenticating...' : authMode === 'signup' ? 'Create Account' : 'Sign In'}
              </button>

              <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => {
                    setAuthModalOpen(false);
                    const demoUser = { user_id: 'demo-user', username: 'demo-user', full_name: 'Demo Learner' };
                    setCurrentUser(demoUser);
                    localStorage.removeItem('cloudlearn_token');
                    localStorage.setItem('cloudlearn_user', JSON.stringify(demoUser));
                    reloadAllUserData('demo-user');
                  }}
                  style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '0.78rem', textDecoration: 'underline', cursor: 'pointer' }}
                >
                  Or continue as Demo User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 2: DSA PROBLEM LOG MODAL                           */}
      {/* ======================================================== */}
      {dsaModalOpen && (
        <div className="auth-modal-overlay" onClick={() => setDsaModalOpen(false)}>
          <div className="auth-modal-card" style={{ maxWidth: '520px' }} onClick={(e) => e.stopPropagation()}>
            <div className="auth-modal-header">
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc', fontWeight: 800 }}>
                Log Solved DSA Problem
              </h3>
              <button
                type="button"
                onClick={() => setDsaModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleLogDsaProblem} className="auth-form-body">
              <div className="form-row">
                <label className="form-label">Problem Title:</label>
                <input
                  type="text"
                  className="text-input"
                  placeholder="e.g. Two Sum, LRU Cache, Merge Intervals"
                  value={dsaForm.problem_title}
                  onChange={(e) => setDsaForm({ ...dsaForm, problem_title: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-row">
                  <label className="form-label">Platform:</label>
                  <select
                    className="select-input"
                    value={dsaForm.platform}
                    onChange={(e) => setDsaForm({ ...dsaForm, platform: e.target.value })}
                  >
                    <option value="LeetCode">LeetCode</option>
                    <option value="Codeforces">Codeforces</option>
                    <option value="GeeksforGeeks">GeeksforGeeks</option>
                    <option value="HackerRank">HackerRank</option>
                    <option value="InterviewBit">InterviewBit</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="form-row">
                  <label className="form-label">Difficulty:</label>
                  <select
                    className="select-input"
                    value={dsaForm.difficulty}
                    onChange={(e) => setDsaForm({ ...dsaForm, difficulty: e.target.value })}
                  >
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-row">
                  <label className="form-label">Topic / Pattern:</label>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="e.g. Arrays, DP, Trees"
                    value={dsaForm.topic}
                    onChange={(e) => setDsaForm({ ...dsaForm, topic: e.target.value })}
                  />
                </div>

                <div className="form-row">
                  <label className="form-label">Date Solved:</label>
                  <input
                    type="date"
                    className="text-input"
                    value={dsaForm.activity_date}
                    onChange={(e) => setDsaForm({ ...dsaForm, activity_date: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <label className="form-label">Problem URL (Optional):</label>
                <input
                  type="url"
                  className="text-input"
                  placeholder="https://leetcode.com/problems/..."
                  value={dsaForm.problem_url}
                  onChange={(e) => setDsaForm({ ...dsaForm, problem_url: e.target.value })}
                />
              </div>

              <div className="form-row">
                <label className="form-label">Key Takeaway / Notes (Optional):</label>
                <textarea
                  className="text-input"
                  rows={2}
                  placeholder="e.g. Used HashMap for O(n) lookup. Beware of edge case with duplicate elements."
                  value={dsaForm.notes}
                  onChange={(e) => setDsaForm({ ...dsaForm, notes: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ flex: 1, justifyContent: 'center' }}
                  onClick={() => setDsaModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={dsaSubmitting}
                  style={{ flex: 1, justifyContent: 'center' }}
                >
                  {dsaSubmitting ? 'Recording...' : 'Save to Heatmap'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 3: STUDY CALENDAR TASK MODAL (ADD / EDIT)          */}
      {/* ======================================================== */}
      {taskModalOpen && (
        <div className="auth-modal-overlay" onClick={() => setTaskModalOpen(false)}>
          <div className="auth-modal-card" style={{ maxWidth: '520px' }} onClick={(e) => e.stopPropagation()}>
            <div className="auth-modal-header">
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc', fontWeight: 800 }}>
                {editingTask ? 'Edit Study Task' : 'Schedule Study Task'}
              </h3>
              <button
                type="button"
                onClick={() => setTaskModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveTask} className="auth-form-body">
              <div className="form-row">
                <label className="form-label">Task Title:</label>
                <input
                  type="text"
                  className="text-input"
                  placeholder="e.g. Revise OS Deadlock Conditions & Coffman Rules"
                  value={taskForm.title}
                  onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-row">
                  <label className="form-label">Category:</label>
                  <select
                    className="select-input"
                    value={taskForm.category}
                    onChange={(e) => setTaskForm({ ...taskForm, category: e.target.value })}
                  >
                    <option value="DSA">DSA</option>
                    <option value="Core CS">Core CS</option>
                    <option value="System Design">System Design</option>
                    <option value="Revision">Revision</option>
                    <option value="Project">Project</option>
                    <option value="Mock Interview">Mock Interview</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="form-row">
                  <label className="form-label">Priority:</label>
                  <select
                    className="select-input"
                    value={taskForm.priority}
                    onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })}
                  >
                    <option value="high">🔴 High Priority</option>
                    <option value="medium">🟡 Medium Priority</option>
                    <option value="low">🔵 Low Priority</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <label className="form-label">Scheduled Date:</label>
                <input
                  type="date"
                  className="text-input"
                  value={taskForm.task_date}
                  onChange={(e) => setTaskForm({ ...taskForm, task_date: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-row">
                  <label className="form-label">Start Time:</label>
                  <input
                    type="time"
                    className="text-input"
                    value={taskForm.start_time}
                    onChange={(e) => setTaskForm({ ...taskForm, start_time: e.target.value })}
                  />
                </div>

                <div className="form-row">
                  <label className="form-label">End Time:</label>
                  <input
                    type="time"
                    className="text-input"
                    value={taskForm.end_time}
                    onChange={(e) => setTaskForm({ ...taskForm, end_time: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-row">
                <label className="form-label">Description / Study Checklist (Optional):</label>
                <textarea
                  className="text-input"
                  rows={2}
                  placeholder="e.g. Read chapter notes, review Coffman conditions, complete targeted practice quiz."
                  value={taskForm.description}
                  onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ flex: 1, justifyContent: 'center' }}
                  onClick={() => setTaskModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={taskSubmitting}
                  style={{ flex: 1, justifyContent: 'center' }}
                >
                  {taskSubmitting ? 'Saving...' : editingTask ? 'Update Task' : 'Add to Calendar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="footer">
        <p>CloudLearn AI &bull; Agentic Personalized Learning Platform &bull; Neon pgvector & Gemini 3.8 Flash</p>
      </footer>
    </div>
  );
}

function chr(code) {
  return String.fromCharCode(code);
}
