const API_BASE = "http://localhost:8000/api/v1";

export function getActiveUserId(): string {
  return localStorage.getItem("student_id") || "";
}

export function setActiveUser(userId: string, userName: string): void {
  localStorage.setItem("student_id", userId);
  localStorage.setItem("student_name", userName);
}

export function getActiveUserName(): string {
  return localStorage.getItem("student_name") || "Student";
}

export function getActiveCourseId(): string {
  return localStorage.getItem("selected_course_id") || "";
}

export function setActiveCourseId(courseId: string): void {
  if (courseId) {
    localStorage.setItem("selected_course_id", courseId);
  } else {
    localStorage.removeItem("selected_course_id");
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  const response = await fetch(url, {
    ...options,
    headers: options.body instanceof FormData ? undefined : headers
  });

  const json = await response.json();
  if (!response.ok || json.success === false) {
    const errorMsg = json.error?.message || `Request failed with status ${response.status}`;
    throw new Error(errorMsg);
  }
  return json.data;
}

export const api = {
  // Users & Onboarding
  getUserStatus: (userId?: string) =>
    request<{ exists: boolean; onboarding_completed: boolean; user: any | null }>(
      `/users/status${userId ? `?user_id=${encodeURIComponent(userId)}` : ""}`
    ),
  onboardUser: (data: { name: string; email?: string; user_id?: string }) =>
    request<any>("/users/onboard", { method: "POST", body: JSON.stringify(data) }),
  getCurrentUser: (userId?: string) =>
    request<any>(`/users/me${userId ? `?user_id=${encodeURIComponent(userId)}` : ""}`),
  listStudents: () => request<any[]>("/users"),

  // Courses
  listCourses: (userId?: string) => {
    const uid = userId || getActiveUserId();
    return request<any[]>(`/courses${uid ? `?user_id=${encodeURIComponent(uid)}` : ""}`);
  },
  getCourse: (courseId: string) => request<any>(`/courses/${courseId}`),
  createCourse: (data: { title: string; code?: string; description?: string; subject?: string; user_id?: string }) => {
    const payload = { ...data, user_id: data.user_id || getActiveUserId() };
    return request<any>("/courses", { method: "POST", body: JSON.stringify(payload) });
  },
  deleteCourse: (courseId: string) => request<any>(`/courses/${courseId}`, { method: "DELETE" }),
  getKnowledgeGraph: (courseId: string) => request<any>(`/courses/${courseId}/knowledge-graph`),

  // Documents
  listCourseDocuments: (courseId: string) => request<any[]>(`/documents/course/${courseId}`),
  deleteDocument: (documentId: string) => request<any>(`/documents/${documentId}`, { method: "DELETE" }),
  getDocumentStatus: (docId: string) => request<any>(`/documents/${docId}/status`),
  uploadDocument: async (courseId: string, file: File, sourceCategory = "course_source") => {
    const formData = new FormData();
    formData.append("course_id", courseId);
    formData.append("source_category", sourceCategory);
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: "POST",
      body: formData
    });
    const json = await res.json();
    if (!res.ok || json.success === false) {
      throw new Error(json.error?.message || "Upload failed");
    }
    return json.data;
  },
  uploadDocumentsBatch: async (courseId: string, files: File[], sourceCategory = "course_source") => {
    const formData = new FormData();
    formData.append("course_id", courseId);
    formData.append("source_category", sourceCategory);
    files.forEach(file => {
      formData.append("files", file);
    });

    const res = await fetch(`${API_BASE}/documents/upload-batch`, {
      method: "POST",
      body: formData
    });
    const json = await res.json();
    if (!res.ok || json.success === false) {
      throw new Error(json.error?.message || "Batch upload failed");
    }
    return json.data;
  },
  ingestYouTubeVideo: (data: { course_id: string; url: string; title?: string; source_category?: string }) =>
    request<any>("/documents/youtube", { method: "POST", body: JSON.stringify(data) }),

  // Chat
  listChatSessions: (userId?: string) => {
    const uid = userId || getActiveUserId();
    return request<any[]>(`/chat/sessions${uid ? `?user_id=${encodeURIComponent(uid)}` : ""}`);
  },
  getChatSession: (chatId: string) => request<any>(`/chat/sessions/${chatId}`),
  createChatSession: (data: { user_id?: string; course_id?: string; title?: string; topic?: string }) => {
    const payload = { ...data, user_id: data.user_id || getActiveUserId() };
    return request<any>("/chat/sessions", { method: "POST", body: JSON.stringify(payload) });
  },
  updateChatSession: (chatId: string, data: { title?: string; pinned?: boolean; course_id?: string | null }) =>
    request<any>(`/chat/sessions/${chatId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteChatSession: (chatId: string) =>
    request<any>(`/chat/sessions/${chatId}`, { method: "DELETE" }),
  sendMessage: (chatId: string, data: { message: string; allow_outside_knowledge?: boolean; user_id?: string; course_id?: string }) => {
    const payload = { ...data, user_id: data.user_id || getActiveUserId() };
    return request<any>(`/chat/sessions/${chatId}/messages`, { method: "POST", body: JSON.stringify(payload) });
  },

  // Assessments
  generateAssessment: (data: {
    user_id?: string;
    course_id?: string;
    topic_id?: string;
    custom_prompt?: string;
    question_type?: string;
    difficulty?: string;
    question_count?: number;
    duration_minutes?: number;
    is_diagnostic?: boolean;
  }) => {
    const payload = { ...data, user_id: data.user_id || getActiveUserId() };
    return request<any>("/assessments/generate", { method: "POST", body: JSON.stringify(payload) });
  },
  getAssessment: (assessmentId: string) => request<any>(`/assessments/${assessmentId}`),
  submitAssessment: (assessmentId: string, answers: { question_id: string; selected_answer: string; time_taken_seconds?: number }[], userId?: string) => {
    const payload = { answers, user_id: userId || getActiveUserId() };
    return request<any>(`/assessments/${assessmentId}/submit`, { method: "POST", body: JSON.stringify(payload) });
  },

  // Learner & Analytics
  getLearnerProfile: (userId?: string) => {
    const uid = userId || getActiveUserId();
    return request<any>(`/learner/profile${uid ? `?user_id=${encodeURIComponent(uid)}` : ""}`);
  },
  getTopicMastery: (userId?: string) => {
    const uid = userId || getActiveUserId();
    return request<any[]>(`/learner/mastery${uid ? `?user_id=${encodeURIComponent(uid)}` : ""}`);
  },
  getPredictions: (concept?: string, userId?: string) => {
    const uid = userId || getActiveUserId();
    const params = new URLSearchParams();
    if (concept) params.append("concept_name", concept);
    if (uid) params.append("user_id", uid);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<any>(`/learner/predictions${qs}`);
  },
  getRecommendations: (userId?: string) => {
    const uid = userId || getActiveUserId();
    return request<any[]>(`/learner/recommendations${uid ? `?user_id=${encodeURIComponent(uid)}` : ""}`);
  },
  getAnalytics: (userId?: string) => {
    const uid = userId || getActiveUserId();
    return request<any>(`/analytics/progress${uid ? `?user_id=${encodeURIComponent(uid)}` : ""}`);
  },
  getMemory: (userId?: string) => {
    const uid = userId || getActiveUserId();
    return request<any>(`/memory/relevant${uid ? `?user_id=${encodeURIComponent(uid)}` : ""}`);
  },
  submitFeedback: (category: string, rating: number, comment: string, userId?: string) => {
    const payload = { category, rating, comment, user_id: userId || getActiveUserId() };
    return request<any>("/memory/feedback", { method: "POST", body: JSON.stringify(payload) });
  }
};
