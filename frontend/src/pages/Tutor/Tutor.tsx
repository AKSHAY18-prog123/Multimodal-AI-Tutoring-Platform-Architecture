import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Bot, 
  User as UserIcon, 
  FileText, 
  ExternalLink, 
  Plus, 
  Search, 
  Pin, 
  Trash2, 
  Sparkles, 
  AlertCircle,
  MessageSquare,
  BookOpen
} from 'lucide-react';
import { api, getActiveCourseId, setActiveCourseId } from '../../services/api';
import { ChatSession, ChatMessage, Citation, Course } from '../../types';
import { SourceViewerDrawer } from '../../components/sources/SourceViewerDrawer';

export const Tutor: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>(() => getActiveCourseId() || 'all');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [allowOutside, setAllowOutside] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Canonical source viewer drawer state
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat sessions & courses on mount
  useEffect(() => {
    loadSessions();
    loadCourses();
  }, []);

  async function loadCourses() {
    try {
      const cList = await api.listCourses();
      setCourses(cList);
      const stored = getActiveCourseId();
      if (stored && cList.find(c => c.id === stored)) {
        setSelectedCourseId(stored);
      } else if (cList.length > 0 && selectedCourseId === 'all') {
        setSelectedCourseId(cList[0].id);
        setActiveCourseId(cList[0].id);
      }
    } catch (e) {
      console.error("Failed to load courses in Tutor:", e);
    }
  }

  // When active session changes, load its message history
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
      const activeObj = sessions.find(s => s.id === activeSessionId);
      if (activeObj?.course_id) {
        setSelectedCourseId(activeObj.course_id);
      }
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function loadSessions() {
    try {
      const data = await api.listChatSessions();
      setSessions(data);
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id);
        if (data[0].course_id) {
          setSelectedCourseId(data[0].course_id);
        }
      }
    } catch (e) {
      console.error("Failed to load sessions:", e);
    }
  }

  async function loadMessages(sessionId: string) {
    try {
      const data = await api.getChatSession(sessionId);
      setMessages(data?.messages || []);
      if (data?.course_id) {
        setSelectedCourseId(data.course_id);
      }
    } catch (e) {
      console.error("Failed to load messages:", e);
    }
  }

  async function handleCourseScopeChange(newCourseId: string) {
    setSelectedCourseId(newCourseId);
    if (newCourseId !== 'all') {
      setActiveCourseId(newCourseId);
    }
    if (activeSessionId) {
      try {
        await api.updateChatSession(activeSessionId, { course_id: newCourseId !== 'all' ? newCourseId : null });
        setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, course_id: newCourseId !== 'all' ? newCourseId : undefined } : s));
      } catch (err) {
        console.error("Failed to update session course_id:", err);
      }
    }
  }

  async function createNewChat() {
    try {
      const session = await api.createChatSession({ 
        title: "New Conversation",
        course_id: selectedCourseId !== 'all' ? selectedCourseId : undefined
      });
      setSessions(prev => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
    } catch (e) {
      console.error("Failed to create new chat:", e);
    }
  }

  async function deleteChat(sessionId: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await api.deleteChatSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter(s => s.id !== sessionId);
        setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch (e) {
      console.error("Failed to delete chat:", e);
    }
  }

  async function togglePin(sessionId: string, e: React.MouseEvent) {
    e.stopPropagation();
    const current = sessions.find(s => s.id === sessionId);
    if (!current) return;
    try {
      const updated = await api.updateChatSession(sessionId, { pinned: !current.pinned });
      setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, pinned: updated.pinned ?? !current.pinned } : s));
    } catch (e) {
      console.error("Failed to toggle pin:", e);
    }
  }

  async function handleSendMessage(customPrompt?: string, explicitOutside: boolean = false) {
    const textToSend = customPrompt || inputMessage;
    if (!textToSend.trim() || loading) return;

    let targetSessionId = activeSessionId;

    // Create session on first message if none active
    if (!targetSessionId) {
      try {
        const newSession = await api.createChatSession({ 
          title: textToSend.slice(0, 30),
          course_id: selectedCourseId !== 'all' ? selectedCourseId : undefined
        });
        setSessions(prev => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        targetSessionId = newSession.id;
      } catch (e) {
        console.error("Failed to auto-create session:", e);
        return;
      }
    }

    if (!targetSessionId) return;

    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: textToSend,
      citations: [],
      is_outside_knowledge: false,
      outside_knowledge_offered: false,
      suggested_followups: [],
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, tempUserMsg]);
    if (!customPrompt) setInputMessage('');
    setLoading(true);

    try {
      const assistantMsg = await api.sendMessage(targetSessionId, {
        message: textToSend,
        allow_outside_knowledge: explicitOutside || allowOutside,
        course_id: selectedCourseId !== 'all' ? selectedCourseId : undefined
      });
      setMessages(prev => [...prev, assistantMsg]);
      // Update session title in list if changed
      loadSessions();
    } catch (e: any) {
      console.error("Failed to send message:", e);
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${e.message}`,
          citations: [],
          is_outside_knowledge: false,
          outside_knowledge_offered: false,
          suggested_followups: [],
          created_at: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation);
    setDrawerOpen(true);
  };

  const filteredSessions = sessions.filter(s => 
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-[calc(100vh-6.5rem)] rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm transition-colors duration-200">
      
      {/* Left Sidebar: Multi-Chat History */}
      <div className="w-72 border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 flex flex-col transition-colors duration-200">
        
        {/* New Chat Button */}
        <div className="p-3 border-b border-slate-200 dark:border-slate-800">
          <button
            onClick={createNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-semibold text-sm shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </button>
        </div>

        {/* Search Chats */}
        <div className="p-3 border-b border-slate-200/60 dark:border-slate-800/60">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400 dark:text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-colors"
            />
          </div>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredSessions.map((s) => {
            const isActive = s.id === activeSessionId;
            return (
              <div
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                className={`group flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-white dark:bg-slate-800 text-sky-600 dark:text-sky-400 shadow-2xs font-semibold border border-slate-200/80 dark:border-slate-700'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {s.pinned ? (
                    <Pin className="w-3.5 h-3.5 text-amber-500 shrink-0 fill-amber-500" />
                  ) : (
                    <MessageSquare className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 shrink-0" />
                  )}
                  <span className="truncate">{s.title}</span>
                </div>

                <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => togglePin(s.id, e)}
                    className="p-1 text-slate-400 hover:text-amber-500 rounded cursor-pointer"
                    title={s.pinned ? "Unpin chat" : "Pin chat"}
                  >
                    <Pin className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => deleteChat(s.id, e)}
                    className="p-1 text-slate-400 hover:text-red-500 rounded cursor-pointer"
                    title="Delete chat"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Conversation Window */}
      <div className="flex-1 flex flex-col bg-white dark:bg-slate-900 transition-colors duration-200">
        
        {/* Tutor Conversation Header with Course Focus Selector */}
        <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-sky-600 dark:text-sky-400" />
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                Course Scope:
              </label>
            </div>
            <select
              value={selectedCourseId}
              onChange={(e) => handleCourseScopeChange(e.target.value)}
              className="px-3 py-1.5 text-xs font-bold rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 shadow-2xs focus:outline-sky-500 cursor-pointer"
            >
              <option value="all">🌐 All Uploaded Courses</option>
              {courses.map(c => (
                <option key={c.id} value={c.id}>📘 {c.title}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
            {selectedCourseId && selectedCourseId !== 'all' ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sky-50 dark:bg-sky-950/70 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800 text-[11px] font-semibold">
                <Sparkles className="w-3 h-3 text-sky-500" />
                Answering from: <strong>{courses.find(c => c.id === selectedCourseId)?.title || 'Selected Course'}</strong>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-[11px]">
                Cross-course knowledge search enabled
              </span>
            )}
          </div>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center shadow-xs">
                <Bot className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">SynapseTutor Grounded Assistant</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Ask any question from your course materials. Every response provides verifiable source citations,
                  adapts to your mastery level, and strictly refuses off-material inquiries unless requested.
                </p>
              </div>

              {/* Starter Prompts */}
              <div className="w-full space-y-2 pt-2 text-left">
                {[
                  "Provide a clear conceptual breakdown of the primary topics in this course.",
                  "Can we walk through the foundational mechanisms and state rules step by step?",
                  "Give me a targeted practice exercise to test my understanding.",
                  "What is the architecture of the latest NVIDIA GPU? (Off-Material Refusal Test)"
                ].map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(prompt)}
                    className="w-full p-2.5 text-xs text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/60 hover:bg-sky-50/50 dark:hover:bg-sky-950/40 hover:border-sky-200 dark:hover:border-sky-800 border border-slate-200 dark:border-slate-700 rounded-lg text-left transition-colors flex items-center justify-between group cursor-pointer"
                  >
                    <span>{prompt}</span>
                    <Sparkles className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 group-hover:text-sky-500" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-3 max-w-3xl ${m.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold ${
                    m.role === 'user' 
                      ? 'bg-sky-600 text-white' 
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                  }`}
                >
                  {m.role === 'user' ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4 text-sky-600 dark:text-sky-400" />}
                </div>

                <div
                  className={`space-y-3 ${
                    m.role === 'user'
                      ? 'bg-sky-600 text-white rounded-2xl rounded-tr-xs px-4 py-3 text-sm shadow-xs'
                      : 'bg-slate-50 dark:bg-slate-800/90 border border-slate-200/90 dark:border-slate-700/80 rounded-2xl rounded-tl-xs p-5 text-sm text-slate-800 dark:text-slate-100 shadow-2xs'
                  }`}
                >
                  {/* Outside Knowledge Banner */}
                  {m.is_outside_knowledge && (
                    <div className="px-3 py-1.5 rounded-lg bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border border-amber-200 dark:border-amber-800 text-xs font-medium flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
                      <span>Labeled Outside Knowledge (Not from uploaded course material)</span>
                    </div>
                  )}

                  {/* Message Body */}
                  <div className="whitespace-pre-wrap leading-relaxed space-y-2 text-slate-800 dark:text-slate-100">
                    {m.content}
                  </div>

                  {/* Outside Knowledge Offer Button */}
                  {m.outside_knowledge_offered && (
                    <div className="pt-2">
                      <button
                        onClick={() => handleSendMessage("Yes, explain using outside knowledge", true)}
                        className="px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold text-xs shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        Explain with Outside Knowledge
                      </button>
                    </div>
                  )}

                  {/* Verified Source Citations Chips */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="pt-3 border-t border-slate-200/80 dark:border-slate-700 space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                        Verified Source Citations (Click to open):
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {m.citations.map((cite, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleCitationClick(cite)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-white dark:bg-slate-900 border border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-300 hover:bg-sky-50 dark:hover:bg-sky-950/50 hover:border-sky-400 shadow-2xs transition-all cursor-pointer"
                          >
                            <FileText className="w-3 h-3 text-sky-600 dark:text-sky-400" />
                            {cite.label}
                            <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suggested Follow-up Pills */}
                  {m.suggested_followups && m.suggested_followups.length > 0 && (
                    <div className="pt-2 space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 block">Suggested next questions:</span>
                      <div className="flex flex-wrap gap-2">
                        {m.suggested_followups.map((f, fIdx) => (
                          <button
                            key={fIdx}
                            onClick={() => handleSendMessage(f)}
                            className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-200/80 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 border border-slate-300/50 dark:border-slate-600 transition-colors cursor-pointer"
                          >
                            {f}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 text-xs py-2">
              <div className="w-7 h-7 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                <Bot className="w-4 h-4 text-sky-600 dark:text-sky-400 animate-spin" />
              </div>
              <span className="animate-pulse">Retrieving multimodal course chunks & validating citations...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 transition-colors duration-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask anything about the course materials..."
              disabled={loading}
              className="flex-1 px-4 py-2.5 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all"
            />
            <button
              type="submit"
              disabled={loading || !inputMessage.trim()}
              className="px-4 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white font-semibold text-sm shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Send className="w-4 h-4" />
              <span>Send</span>
            </button>
          </form>

          {/* Controls Footer */}
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 pt-2 px-1">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={allowOutside}
                onChange={(e) => setAllowOutside(e.target.checked)}
                className="rounded border-slate-300 dark:border-slate-700 text-sky-600 focus:ring-sky-500 bg-white dark:bg-slate-900"
              />
              <span>Allow Outside Knowledge if material lacks coverage</span>
            </label>
            <span className="text-[11px] text-slate-400 dark:text-slate-500">Strictly Source-Attributed Model</span>
          </div>
        </div>
      </div>

      {/* Slide-over Canonical Source Viewer Drawer */}
      <SourceViewerDrawer
        citation={selectedCitation}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
};
