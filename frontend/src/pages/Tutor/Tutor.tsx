import React, { useState, useEffect, useRef } from 'react';
import { 
  Plus, 
  Search, 
  Pin, 
  Trash2, 
  Send, 
  Bot, 
  User as UserIcon, 
  FileText, 
  AlertCircle, 
  Sparkles, 
  BookOpen, 
  ExternalLink,
  MessageSquare
} from 'lucide-react';
import { api } from '../../services/api';
import { ChatSession, ChatMessage, Citation } from '../../types';
import { SourceViewerDrawer } from '../../components/sources/SourceViewerDrawer';

export const Tutor: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [allowOutside, setAllowOutside] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [courses, setCourses] = useState<any[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');

  // Load chat sessions & courses on mount
  useEffect(() => {
    async function init() {
      try {
        const cList = await api.listCourses();
        setCourses(cList);
        if (cList.length > 0) setSelectedCourseId(cList[0].id);
      } catch (err) {
        console.error("Failed to load courses for tutor:", err);
      }
      loadSessions();
    }
    init();
  }, []);

  // When active session changes, load messages
  useEffect(() => {
    if (activeSessionId) {
      loadSessionMessages(activeSessionId);
    }
  }, [activeSessionId]);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function loadSessions() {
    try {
      const data = await api.listChatSessions();
      setSessions(data);
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id);
      } else if (data.length === 0) {
        createNewChat();
      }
    } catch (e) {
      console.error("Failed to load sessions:", e);
    }
  }

  async function loadSessionMessages(sessionId: string) {
    try {
      const data = await api.getChatSession(sessionId);
      setMessages(data.messages || []);
      if (data.course_id) setSelectedCourseId(data.course_id);
    } catch (e) {
      console.error("Failed to load messages:", e);
    }
  }

  async function createNewChat() {
    try {
      const targetCourse = selectedCourseId || (courses.length > 0 ? courses[0].id : undefined);
      const newChat = await api.createChatSession({
        title: "New Conversation",
        course_id: targetCourse
      });
      setSessions(prev => [newChat, ...prev]);
      setActiveSessionId(newChat.id);
      setMessages([]);
    } catch (e) {
      console.error("Failed to create chat:", e);
    }
  }

  async function togglePin(sessionId: string, e: React.MouseEvent) {
    e.stopPropagation();
    const session = sessions.find(s => s.id === sessionId);
    if (!session) return;
    try {
      await api.updateChatSession(sessionId, { pinned: !session.pinned });
      setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, pinned: !s.pinned } : s));
    } catch (err) {
      console.error(err);
    }
  }

  async function deleteChat(sessionId: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await api.deleteChatSession(sessionId);
      const remaining = sessions.filter(s => s.id !== sessionId);
      setSessions(remaining);
      if (activeSessionId === sessionId) {
        setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function handleSendMessage(customText?: string, explicitOutside = false) {
    const textToSend = customText || inputMessage;
    if (!textToSend.trim() || !activeSessionId || loading) return;

    setInputMessage('');
    const userMsgTemp: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: textToSend,
      citations: [],
      is_outside_knowledge: false,
      outside_knowledge_offered: false,
      suggested_followups: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsgTemp]);
    setLoading(true);

    try {
      const assistantMsg = await api.sendMessage(activeSessionId, {
        message: textToSend,
        allow_outside_knowledge: explicitOutside || allowOutside
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
    <div className="flex h-[calc(100vh-6.5rem)] rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm animate-fade-in">
      {/* Left Sidebar: Multi-Chat History */}
      <div className="w-72 border-r border-slate-200 bg-slate-50/70 flex flex-col">
        {/* New Chat Button */}
        <div className="p-3 border-b border-slate-200">
          <button
            onClick={createNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm shadow-xs transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </button>
        </div>

        {/* Search Chats */}
        <div className="p-3 border-b border-slate-200/60">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
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
                    ? 'bg-white text-brand-700 shadow-2xs font-semibold border border-slate-200/80'
                    : 'text-slate-600 hover:bg-slate-200/50 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {s.pinned ? (
                    <Pin className="w-3.5 h-3.5 text-amber-500 shrink-0 fill-amber-500" />
                  ) : (
                    <MessageSquare className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  )}
                  <span className="truncate">{s.title}</span>
                </div>

                <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => togglePin(s.id, e)}
                    className="p-1 text-slate-400 hover:text-amber-600 rounded"
                    title={s.pinned ? "Unpin chat" : "Pin chat"}
                  >
                    <Pin className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => deleteChat(s.id, e)}
                    className="p-1 text-slate-400 hover:text-red-600 rounded"
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
      <div className="flex-1 flex flex-col bg-white">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center shadow-xs">
                <Bot className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">SynapseTutor Grounded Assistant</h3>
                <p className="text-xs text-slate-500 mt-1">
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
                    className="w-full p-2.5 text-xs text-slate-700 bg-slate-50 hover:bg-brand-50/50 hover:border-brand-200 border border-slate-200 rounded-lg text-left transition-colors flex items-center justify-between group cursor-pointer"
                  >
                    <span>{prompt}</span>
                    <Sparkles className="w-3.5 h-3.5 text-slate-400 group-hover:text-brand-500" />
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
                    m.role === 'user' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700 border border-slate-200'
                  }`}
                >
                  {m.role === 'user' ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4 text-brand-600" />}
                </div>

                <div
                  className={`space-y-3 ${
                    m.role === 'user'
                      ? 'bg-brand-600 text-white rounded-2xl rounded-tr-xs px-4 py-3 text-sm shadow-xs'
                      : 'bg-slate-50/80 border border-slate-200 rounded-2xl rounded-tl-xs p-5 text-sm text-slate-800 shadow-2xs'
                  }`}
                >
                  {/* Outside Knowledge Banner */}
                  {m.is_outside_knowledge && (
                    <div className="px-3 py-1.5 rounded-lg bg-amber-100 text-amber-900 border border-amber-200 text-xs font-medium flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>Labeled Outside Knowledge (Not from uploaded course material)</span>
                    </div>
                  )}

                  {/* Message Body */}
                  <div className="whitespace-pre-wrap leading-relaxed space-y-2">
                    {m.content}
                  </div>

                  {/* Outside Knowledge Offer Button */}
                  {m.outside_knowledge_offered && (
                    <div className="pt-2">
                      <button
                        onClick={() => handleSendMessage("Yes, explain using outside knowledge", true)}
                        className="px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold text-xs shadow-xs transition-colors flex items-center gap-1.5"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        Explain with Outside Knowledge
                      </button>
                    </div>
                  )}

                  {/* Verified Source Citations Chips */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="pt-3 border-t border-slate-200/80 space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                        Verified Source Citations (Click to open):
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {m.citations.map((cite, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleCitationClick(cite)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-white border border-brand-200 text-brand-700 hover:bg-brand-50 hover:border-brand-400 shadow-2xs transition-all cursor-pointer"
                          >
                            <FileText className="w-3 h-3 text-brand-600" />
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
                      <span className="text-[11px] font-semibold text-slate-400 block">Suggested next questions:</span>
                      <div className="flex flex-wrap gap-2">
                        {m.suggested_followups.map((f, fIdx) => (
                          <button
                            key={fIdx}
                            onClick={() => handleSendMessage(f)}
                            className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-200/70 hover:bg-slate-300 text-slate-700 transition-colors"
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
            <div className="flex items-center gap-3 text-slate-500 text-xs py-2">
              <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center">
                <Bot className="w-4 h-4 text-brand-600 animate-spin" />
              </div>
              <span className="animate-pulse">Retrieving multimodal course chunks & validating citations...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-200 bg-white">
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
              className="flex-1 px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
            />
            <button
              type="submit"
              disabled={loading || !inputMessage.trim()}
              className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold text-sm shadow-xs transition-colors flex items-center gap-1.5"
            >
              <Send className="w-4 h-4" />
              <span>Send</span>
            </button>
          </form>

          {/* Controls Footer */}
          <div className="flex items-center justify-between text-xs text-slate-500 pt-2 px-1">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={allowOutside}
                onChange={(e) => setAllowOutside(e.target.checked)}
                className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              <span>Allow Outside Knowledge if material lacks coverage</span>
            </label>
            <span className="text-[11px] text-slate-400">Strictly Source-Attributed Model</span>
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
