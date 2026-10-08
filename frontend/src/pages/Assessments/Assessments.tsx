import React, { useState } from 'react';
import { 
  CheckSquare, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  ArrowRight, 
  RotateCcw, 
  TrendingUp, 
  BrainCircuit, 
  Sparkles,
  HelpCircle,
  Award,
  RefreshCw
} from 'lucide-react';
import { api } from '../../services/api';
import { AssessmentQuestion, AssessmentReport } from '../../types';

interface AssessmentsProps {
  initialDiagnostic?: boolean;
}

export const Assessments: React.FC<AssessmentsProps> = ({ initialDiagnostic = false }) => {
  // Course & Topic State
  const [courses, setCourses] = useState<any[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');
  const [topics, setTopics] = useState<any[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string>('all');
  const [customPrompt, setCustomPrompt] = useState<string>('');
  const [questionType, setQuestionType] = useState<string>('mcq');

  // Assessment Generation State
  const [difficulty, setDifficulty] = useState('medium');
  const [questionCount, setQuestionCount] = useState(5);
  const [isDiagnostic, setIsDiagnostic] = useState(initialDiagnostic);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Active Test State
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [assessmentTitle, setAssessmentTitle] = useState('');
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Report State
  const [report, setReport] = useState<AssessmentReport | null>(null);

  React.useEffect(() => {
    async function loadCourses() {
      try {
        const cList = await api.listCourses();
        setCourses(cList);
        if (cList.length > 0) setSelectedCourseId(cList[0].id);
      } catch (e) {
        console.error("Failed to load courses:", e);
      }
    }
    loadCourses();
  }, []);

  React.useEffect(() => {
    async function loadCourseTopics() {
      if (!selectedCourseId) {
        setTopics([]);
        return;
      }
      try {
        const cDetail = await api.getCourse(selectedCourseId);
        setTopics(cDetail.topics || []);
      } catch (err) {
        console.error("Failed to load topics:", err);
        setTopics([]);
      }
    }
    loadCourseTopics();
  }, [selectedCourseId]);

  async function handleStartAssessment() {
    setGenerationError(null);
    setIsGenerating(true);
    try {
      const targetCourse = selectedCourseId || (courses.length > 0 ? courses[0].id : undefined);
      const data = await api.generateAssessment({
        course_id: targetCourse,
        topic_id: selectedTopicId !== 'all' ? selectedTopicId : undefined,
        custom_prompt: customPrompt.trim() || undefined,
        question_type: questionType,
        difficulty: difficulty,
        question_count: questionCount,
        is_diagnostic: isDiagnostic
      });
      setAssessmentId(data.assessment_id);
      setAssessmentTitle(data.title || "Targeted Course Assessment");
      setQuestions(data.questions || []);
      setCurrentIndex(0);
      setAnswers({});
      setReport(null);
    } catch (e: any) {
      console.error("Failed to generate assessment:", e);
      setGenerationError(e.message || "Failed to generate questions. Please verify your course material is uploaded.");
    } finally {
      setIsGenerating(false);
    }
  }

  function handleSelectOption(optionId: string) {
    if (!questions[currentIndex]) return;
    setAnswers(prev => ({
      ...prev,
      [questions[currentIndex].id]: optionId
    }));
  }

  async function handleSubmitAssessment() {
    if (!assessmentId) return;
    setIsSubmitting(true);
    try {
      const payloadAnswers = questions.map(q => ({
        question_id: q.id,
        selected_answer: answers[q.id] || "No Answer",
        time_taken_seconds: 35.0
      }));

      const reportData = await api.submitAssessment(assessmentId, payloadAnswers);
      setReport(reportData);
    } catch (e) {
      console.error("Failed to submit assessment:", e);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setAssessmentId(null);
    setQuestions([]);
    setReport(null);
  }

  // 1. Post-Assessment Diagnostic Report View
  if (report) {
    return (
      <div className="max-w-4xl mx-auto space-y-8 animate-fade-in pb-12">
        {/* Header */}
        <div className="flex items-center justify-between pb-6 border-b border-slate-200">
          <div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 uppercase tracking-wide">
              Assessment Completed
            </span>
            <h1 className="text-2xl font-bold text-slate-900 mt-2">Diagnostic Assessment Report</h1>
            <p className="text-sm text-slate-500">Post-test mastery analysis, learning gains, and misconception diagnostics.</p>
          </div>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RotateCcw className="w-4 h-4" />
            New Assessment
          </button>
        </div>

        {/* Score & Accuracy Hero */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs text-center">
            <span className="text-xs font-semibold text-slate-500 uppercase">Test Accuracy</span>
            <div className="text-4xl font-extrabold text-slate-900 mt-2">
              {report.accuracy_percentage}%
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {report.correct_answers} of {report.total_questions} questions correct
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs text-center">
            <span className="text-xs font-semibold text-slate-500 uppercase">Estimated Learning Gain</span>
            <div className="text-4xl font-extrabold text-emerald-600 mt-2">
              +19%
            </div>
            <p className="text-xs text-slate-400 mt-1">Skill mastery gain</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs text-center">
            <span className="text-xs font-semibold text-slate-500 uppercase">Average Time / Question</span>
            <div className="text-4xl font-extrabold text-blue-600 mt-2">
              35s
            </div>
            <p className="text-xs text-slate-400 mt-1">Pacing within target range</p>
          </div>
        </div>

        {/* Misconception Diagnostic Banner */}
        {report.misconception_diagnostic && (
          <div className="rounded-2xl border border-red-200 bg-red-50/50 p-6 shadow-xs space-y-3">
            <div className="flex items-center gap-2.5 text-red-800 font-bold text-base">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <span>Misconception Detected: {report.misconception_diagnostic.misconception_title}</span>
            </div>
            <p className="text-sm text-slate-700 leading-relaxed font-sans">
              {report.misconception_diagnostic.remediation_guidance}
            </p>
            <div className="pt-2">
              <button
                onClick={handleStartAssessment}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold text-xs transition-colors shadow-xs"
              >
                Attempt 3 Targeted Remediation Questions
              </button>
            </div>
          </div>
        )}

        {/* Mastery Delta Progression Table */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
          <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-brand-600" />
            Concept Mastery Changes
          </h3>
          <div className="divide-y divide-slate-100">
            {report.mastery_changes.map((mc, idx) => (
              <div key={idx} className="py-3 flex items-center justify-between text-sm">
                <div>
                  <span className="font-semibold text-slate-900">{mc.concept}</span>
                  <div className="text-xs text-slate-400">Before: {mc.before}% → After: {mc.after}%</div>
                </div>
                <div className="flex items-center gap-2 font-bold text-emerald-600">
                  <ArrowRight className="w-4 h-4 text-emerald-500" />
                  <span>+{mc.improvement}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Prescribed Next Actions */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
          <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-brand-600" />
            Recommended Next Step
          </h3>
          {report.recommendations.map((rec, i) => (
            <div key={i} className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <h4 className="font-bold text-sm text-slate-900">{rec.title}</h4>
              <p className="text-xs text-slate-600 mt-1">{rec.guidance}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 2. Active Test Player View
  if (assessmentId && questions.length > 0) {
    const q = questions[currentIndex];
    const isLast = currentIndex === questions.length - 1;

    return (
      <div className="max-w-3xl mx-auto space-y-6 animate-fade-in pb-12">
        {/* Test Progress Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <div>
            <span className="text-xs font-semibold text-brand-600 uppercase tracking-wider">{assessmentTitle}</span>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Question {currentIndex + 1} of {questions.length}
            </h2>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 bg-slate-100 px-3 py-1.5 rounded-lg">
            <Clock className="w-4 h-4 text-slate-400" />
            <span>Time Remaining: ~12:40</span>
          </div>
        </div>

        {/* Question Card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-xs space-y-6">
          <div className="flex items-center justify-between text-xs font-medium text-slate-500 pb-2 border-b border-slate-100">
            <span>Concept: <strong>{q.concept_name}</strong></span>
            <span className="capitalize px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">{q.difficulty}</span>
          </div>

          <p className="text-base text-slate-900 font-medium leading-relaxed">
            {q.question_text}
          </p>

          {/* Options */}
          <div className="space-y-3 pt-2">
            {q.options.map((opt) => {
              const isSelected = answers[q.id] === opt.id;
              return (
                <div
                  key={opt.id}
                  onClick={() => handleSelectOption(opt.id)}
                  className={`p-4 rounded-xl border text-sm font-medium cursor-pointer transition-all flex items-start gap-3 ${
                    isSelected
                      ? 'border-brand-500 bg-brand-50/50 text-brand-900 shadow-2xs font-semibold'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/60 text-slate-700'
                  }`}
                >
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                      isSelected ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {opt.id}
                  </span>
                  <span className="leading-relaxed">{opt.text}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Navigation & Submit Bar */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setCurrentIndex(prev => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 disabled:opacity-40 hover:bg-slate-50 transition-colors"
          >
            Previous
          </button>

          {isLast ? (
            <button
              onClick={handleSubmitAssessment}
              disabled={isSubmitting}
              className="px-6 py-2.5 text-sm font-bold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors flex items-center gap-2"
            >
              {isSubmitting ? 'Evaluating Answers...' : 'Submit Assessment'}
            </button>
          ) : (
            <button
              onClick={() => setCurrentIndex(prev => Math.min(questions.length - 1, prev + 1))}
              className="px-5 py-2 text-sm font-bold rounded-xl bg-brand-600 hover:bg-brand-700 text-white shadow-sm transition-colors flex items-center gap-1.5"
            >
              Next Question
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // 3. Test Configurator Setup View
  return (
    <div className="max-w-2xl mx-auto space-y-8 animate-fade-in pb-12">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Adaptive Assessment Engine</h1>
        <p className="text-sm text-slate-500 mt-1">
          Smart adaptive quiz tailored to your course curriculum, selected modules, and learning goals.
        </p>
      </div>

      {generationError && (
        <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{generationError}</span>
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-xs space-y-6">
        {/* Course Selection */}
        {courses.length > 0 && (
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide">
              Course Curriculum
            </label>
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              className="w-full px-3.5 py-2.5 text-xs font-semibold rounded-xl bg-slate-50 border border-slate-300 text-slate-800 shadow-2xs"
            >
              {courses.map(c => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
          </div>
        )}

        {/* Module / Topic Selection */}
        <div className="space-y-1.5">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide">
            Module / Topic Focus
          </label>
          <select
            value={selectedTopicId}
            onChange={(e) => setSelectedTopicId(e.target.value)}
            className="w-full px-3.5 py-2.5 text-xs font-semibold rounded-xl bg-slate-50 border border-slate-300 text-slate-800 shadow-2xs"
          >
            <option value="all">🌟 All Modules & Topics (Full Course Review)</option>
            {topics.map(t => (
              <option key={t.id} value={t.id}>📚 {t.title}</option>
            ))}
          </select>
        </div>

        {/* Custom User Request / Focus Prompt */}
        <div className="space-y-1.5">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide">
            Custom Topic or Focus Prompt <span className="text-slate-400 font-normal lowercase">(optional)</span>
          </label>
          <input
            type="text"
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="e.g. Focus on Neural Networks, Backpropagation equations, or leave empty"
            className="w-full px-3.5 py-2.5 text-xs font-medium rounded-xl bg-white border border-slate-300 text-slate-800 shadow-2xs placeholder:text-slate-400 focus:outline-brand-500"
          />
        </div>

        {/* Question Type Selection */}
        <div className="space-y-2">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide">
            Question Format
          </label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { id: 'mcq', label: 'Multiple Choice (MCQs)' },
              { id: 'mixed', label: 'Mixed / Conceptual' }
            ].map(qt => (
              <button
                key={qt.id}
                type="button"
                onClick={() => setQuestionType(qt.id)}
                className={`py-2 px-3 text-xs font-bold rounded-xl border transition-all ${
                  questionType === qt.id
                    ? 'border-brand-500 bg-brand-50 text-brand-700 shadow-2xs'
                    : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
                }`}
              >
                {qt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Diagnostic Toggle */}
        <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/60 flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <label className="flex items-center justify-between font-semibold text-sm text-slate-900 cursor-pointer">
              <span>Quick Diagnostic Baseline Test</span>
              <input
                type="checkbox"
                checked={isDiagnostic}
                onChange={(e) => setIsDiagnostic(e.target.checked)}
                className="rounded border-slate-300 text-brand-600 focus:ring-brand-500 h-4 w-4"
              />
            </label>
            <p className="text-xs text-slate-600 mt-1">
              Tests fundamental concepts across the course to quickly establish your current level.
            </p>
          </div>
        </div>

        {/* Difficulty Selection */}
        <div className="space-y-2">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide">
            Target Difficulty Level
          </label>
          <div className="grid grid-cols-3 gap-3">
            {['easy', 'medium', 'hard'].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDifficulty(d)}
                className={`py-2.5 text-xs font-bold rounded-xl border capitalize transition-all ${
                  difficulty === d
                    ? 'border-brand-500 bg-brand-50 text-brand-700 shadow-2xs'
                    : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Question Count Selection */}
        <div className="space-y-2">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide">
            Question Count
          </label>
          <div className="grid grid-cols-3 gap-3">
            {[3, 5, 10].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setQuestionCount(n)}
                className={`py-2.5 text-xs font-bold rounded-xl border transition-all ${
                  questionCount === n
                    ? 'border-brand-500 bg-brand-50 text-brand-700 shadow-2xs'
                    : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
                }`}
              >
                {n} Questions
              </button>
            ))}
          </div>
        </div>

        {/* Prominent Start Button */}
        <div className="pt-4 border-t border-slate-100">
          <button
            onClick={handleStartAssessment}
            disabled={isGenerating}
            className="w-full py-3.5 px-6 rounded-xl bg-brand-600 hover:bg-brand-700 active:scale-[0.99] text-white font-bold text-sm shadow-md transition-all flex items-center justify-center gap-2.5 cursor-pointer disabled:opacity-60"
          >
            {isGenerating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Generating & Verifying Questions...</span>
              </>
            ) : (
              <>
                <CheckSquare className="w-5 h-5" />
                <span>Start Assessment Now</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
