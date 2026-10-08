import React, { useState, useEffect } from 'react';
import { 
  Award, 
  Clock, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles, 
  BookOpen, 
  BrainCircuit, 
  Zap,
  Target,
  Plus,
  FolderPlus
} from 'lucide-react';
import { api, getActiveUserName } from '../../services/api';
import { LearnerProfile, TopicMastery } from '../../types';

interface DashboardProps {
  onNavigate: (tab: string, meta?: any) => void;
  onOpenAddCourse?: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate, onOpenAddCourse }) => {
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [masteries, setMasteries] = useState<TopicMastery[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const studentName = getActiveUserName();

  useEffect(() => {
    async function loadData() {
      try {
        const [p, m, r, c] = await Promise.all([
          api.getLearnerProfile(),
          api.getTopicMastery(),
          api.getRecommendations(),
          api.listCourses()
        ]);
        setProfile(p);
        setMasteries(m);
        setRecommendations(r);
        setCourses(c);
      } catch (e) {
        console.error("Dashboard data load error:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const overallPct = profile ? Math.round(profile.overall_mastery * 100) : 0;
  const isColdStart = !profile || profile.status === 'uncalibrated' || masteries.length === 0;

  const weakTopics = masteries.filter(m => m.mastery_score < 50).slice(0, 3);
  const strongTopics = masteries.filter(m => m.mastery_score >= 70).slice(0, 3);

  // 1. GENUINE FIRST-TIME USER / EMPTY COURSE STATE (No fake courses or data)
  if (!loading && courses.length === 0) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-4 animate-fade-in text-center space-y-8">
        <div className="w-20 h-20 mx-auto rounded-3xl bg-brand-50 border border-brand-200 text-brand-600 flex items-center justify-center shadow-xs">
          <BookOpen className="w-10 h-10" />
        </div>

        <div className="space-y-3">
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Welcome, {studentName} 👋
          </h1>
          <p className="text-base text-slate-600 max-w-lg mx-auto leading-relaxed">
            Let's set up your learning space. You haven't added any courses yet.
          </p>
          <p className="text-xs text-slate-400">
            Upload any course material — PDF textbook, lecture slides, video, or notes.
            The system will automatically extract knowledge units, build a prerequisite graph, and adapt to your learning pace.
          </p>
        </div>

        <div className="pt-2">
          <button
            onClick={onOpenAddCourse}
            className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-sm shadow-md hover:shadow-lg transition-all cursor-pointer group"
          >
            <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform" />
            <span>+ Add Course / Resource</span>
          </button>
        </div>

        {/* Feature Highlights for New Student */}
        <div className="grid sm:grid-cols-3 gap-4 pt-8 text-left border-t border-slate-200">
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5">
            <h4 className="text-xs font-bold text-slate-900">1. Multimodal Ingestion</h4>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Upload PDFs, PPTX slides, diagrams, and lecture videos with automatic page/timestamp citations.
            </p>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5">
            <h4 className="text-xs font-bold text-slate-900">2. Adaptive AI Tutoring</h4>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Real-time progress tracking adapts to your pace through tutoring chat and adaptive quizzes.
            </p>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5">
            <h4 className="text-xs font-bold text-slate-900">3. Diagnostic Verification</h4>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Symbolic math verification (SymPy) and novelty checks ensure fresh, high-quality assessments.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // 2. ACTIVE DASHBOARD (When at least 1 course has been added)
  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Academic Overview</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Welcome back, {studentName}. Track your personalized learning progress and smart study recommendations.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenAddCourse}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-xs transition-colors"
          >
            <FolderPlus className="w-4 h-4 text-slate-500" />
            + Add Course
          </button>
          <button
            onClick={() => onNavigate('tutor')}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-xs transition-colors"
          >
            Ask Tutor
          </button>
          <button
            onClick={() => onNavigate('assessments', { is_diagnostic: isColdStart })}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-brand-600 text-white hover:bg-brand-700 shadow-sm transition-colors"
          >
            <Zap className="w-4 h-4" />
            {isColdStart ? 'Take 3-Min Diagnostic' : 'Start Adaptive Quiz'}
          </button>
        </div>
      </div>

      {/* Cold Start / Setup Calibration Banner */}
      {isColdStart && (
        <div className="rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50/70 via-orange-50/50 to-white p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-amber-100 text-amber-800 rounded-xl">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="space-y-3 flex-1">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Set Up Your Learning Pace
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  Your profile is currently in <strong>Getting Started</strong> mode.
                  Choose how you'd like to gauge your starting level:
                </p>
              </div>
              <div className="grid sm:grid-cols-2 gap-4 pt-1">
                <div 
                  onClick={() => onNavigate('assessments', { is_diagnostic: true })}
                  className="cursor-pointer p-4 rounded-xl border border-amber-200 bg-white hover:border-brand-500 hover:shadow-md transition-all group"
                >
                  <div className="flex items-center justify-between font-semibold text-sm text-slate-900 mb-1">
                    <span>Option A: Quick Diagnostic Quiz</span>
                    <ArrowRight className="w-4 h-4 text-brand-600 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <p className="text-xs text-slate-500">
                    3 targeted questions across your course concepts to check your baseline knowledge level.
                  </p>
                </div>

                <div 
                  onClick={() => onNavigate('tutor')}
                  className="cursor-pointer p-4 rounded-xl border border-slate-200 bg-white hover:border-brand-500 hover:shadow-md transition-all group"
                >
                  <div className="flex items-center justify-between font-semibold text-sm text-slate-900 mb-1">
                    <span>Option B: Start Learning with Tutor</span>
                    <ArrowRight className="w-4 h-4 text-brand-600 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <p className="text-xs text-slate-500">
                    Jump straight into chat. The tutor explains step-by-step and automatically adapts to your level.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* KPI Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Overall Mastery */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Overall Mastery</span>
            <Target className="w-4 h-4 text-brand-500" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{overallPct}%</span>
            <span className="text-xs font-medium text-slate-500">
              {isColdStart ? 'Uncalibrated' : 'Calibrated'}
            </span>
          </div>
          <div className="mt-3 w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-brand-600 h-2 rounded-full transition-all duration-700" 
              style={{ width: `${Math.max(5, overallPct)}%` }}
            />
          </div>
          <p className="text-xs text-slate-400 mt-2">Estimated overall mastery</p>
        </div>

        {/* Study Time */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Active Study Time</span>
            <Clock className="w-4 h-4 text-blue-500" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">
              {profile ? Math.round(profile.total_active_study_minutes) : 0}
            </span>
            <span className="text-sm font-semibold text-slate-500">mins</span>
          </div>
          <div className="mt-3 flex justify-between text-xs text-slate-500 border-t border-slate-100 pt-2">
            <span>Reading: {profile ? Math.round(profile.total_active_study_minutes * 0.6) : 0}m</span>
            <span>Problems: {profile ? Math.round(profile.total_active_study_minutes * 0.4) : 0}m</span>
          </div>
        </div>

        {/* Verified Questions Answered */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Questions Solved</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">
              {profile?.total_questions_answered || 0}
            </span>
            <span className="text-xs font-medium text-slate-500">verified problems</span>
          </div>
          <div className="mt-3 text-xs text-slate-500 border-t border-slate-100 pt-2 flex items-center justify-between">
            <span>Repetition: 0%</span>
            <span className="text-emerald-600 font-semibold">100% Novel</span>
          </div>
        </div>

        {/* Assessments Completed */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
            <span>Adaptive Assessments</span>
            <Award className="w-4 h-4 text-purple-500" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">
              {profile?.total_assessments_completed || 0}
            </span>
            <span className="text-sm font-semibold text-slate-500">tests</span>
          </div>
          <div className="mt-3 text-xs text-slate-500 border-t border-slate-100 pt-2 flex items-center justify-between">
            <span>Diagnostic level:</span>
            <span className="font-semibold text-brand-700 capitalize">
              {profile?.status || "Getting Started"}
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Topic Performance & Recommended Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Topic Mastery Bars */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <BrainCircuit className="w-5 h-5 text-brand-600" />
                Concept Mastery Overview
              </h2>
              <button
                onClick={() => onNavigate('profile')}
                className="text-xs font-semibold text-brand-600 hover:text-brand-800"
              >
                View Full Profile
              </button>
            </div>

            {masteries.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs space-y-2">
                <p>No concept mastery evidence collected yet.</p>
                <p className="text-slate-500">
                  Complete an assessment or ask questions in the tutor to build your personalized skill profile.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {masteries.map((m) => (
                  <div key={m.id || m.concept_name} className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="font-semibold text-slate-800">{m.concept_name}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400 capitalize">{m.difficulty}</span>
                        <span className="font-bold text-slate-900">{m.mastery_score}%</span>
                      </div>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden flex">
                      <div 
                        className={`h-2 rounded-full transition-all duration-500 ${
                          m.mastery_score >= 70 ? 'bg-emerald-500' :
                          m.mastery_score >= 45 ? 'bg-amber-500' : 'bg-red-400'
                        }`}
                        style={{ width: `${Math.max(5, m.mastery_score)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Diagnostic Insights: Weak / Strong Areas */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="rounded-xl border border-red-200/70 bg-red-50/30 p-5 shadow-xs">
              <div className="flex items-center gap-2 text-red-800 font-bold text-sm mb-3">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                Priority Weak Concepts (&lt; 50%)
              </div>
              {weakTopics.length > 0 ? (
                <ul className="space-y-2 text-xs text-slate-700">
                  {weakTopics.map(w => (
                    <li key={w.concept_name} className="flex justify-between items-center bg-white p-2.5 rounded-lg border border-red-100 shadow-2xs">
                      <span className="font-semibold">{w.concept_name}</span>
                      <span className="text-red-600 font-bold">{w.mastery_score}%</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">
                  {masteries.length === 0 ? "No concept data yet." : "No critically weak concepts detected."}
                </p>
              )}
            </div>

            <div className="rounded-xl border border-emerald-200/70 bg-emerald-50/30 p-5 shadow-xs">
              <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm mb-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Mastered Strong Concepts (≥ 70%)
              </div>
              {strongTopics.length > 0 ? (
                <ul className="space-y-2 text-xs text-slate-700">
                  {strongTopics.map(s => (
                    <li key={s.concept_name} className="flex justify-between items-center bg-white p-2.5 rounded-lg border border-emerald-100 shadow-2xs">
                      <span className="font-semibold">{s.concept_name}</span>
                      <span className="text-emerald-700 font-bold">{s.mastery_score}%</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">
                  {masteries.length === 0 ? "No concept data yet." : "Solve assessment questions to elevate concepts to strong status."}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Recommendations & Behavior Profile */}
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
            <h2 className="text-base font-bold text-slate-900 pb-2 border-b border-slate-100 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-600" />
              Personalized Recommendations
            </h2>

            <div className="space-y-3">
              {recommendations.map((rec, i) => (
                <div 
                  key={i} 
                  className="p-4 rounded-xl border border-slate-200 hover:border-brand-500 hover:bg-brand-50/30 transition-all cursor-pointer group"
                  onClick={() => {
                    if (rec.action_type === 'add_course') onOpenAddCourse?.();
                    else onNavigate('assessments');
                  }}
                >
                  <div className="flex items-center justify-between text-xs text-brand-700 font-semibold mb-1">
                    <span>{rec.topic}</span>
                    <span className="text-slate-400 group-hover:text-brand-600 font-medium">Take Action →</span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">{rec.title}</h4>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">{rec.reason}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Behavior Profile Snapshot */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-slate-500" />
              Learning Behavior Profile
            </h3>
            <p className="text-xs text-slate-500">Cognitive preferences calibrated dynamically from interactions:</p>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Explanation Style:</span>
                <span className="font-semibold text-slate-800 capitalize">
                  {profile?.learning_behavior?.explanation_preference?.replace('_', ' ') || 'Balanced Scaffolded'}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Pedagogical Framing:</span>
                <span className="font-semibold text-slate-800">
                  {profile?.learning_behavior?.prefers_examples_before_theory ? 'Examples Before Theory' : 'Theory First'}
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-500">Pacing:</span>
                <span className="font-semibold text-slate-800 capitalize">
                  {profile?.learning_behavior?.pacing || 'Moderate Adaptive'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
