import React, { useState, useEffect } from 'react';
import { 
  UserCircle, 
  BrainCircuit, 
  Cpu, 
  Clock, 
  TrendingUp, 
  History, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';
import { api, getActiveUserName } from '../../services/api';
import { LearnerProfile as LearnerProfileType, TopicMastery } from '../../types';

export const LearnerProfile: React.FC = () => {
  const [profile, setProfile] = useState<LearnerProfileType | null>(null);
  const [masteries, setMasteries] = useState<TopicMastery[]>([]);
  const [predictions, setPredictions] = useState<any | null>(null);
  const [memoryData, setMemoryData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const studentName = getActiveUserName();
  const initials = studentName
    .split(' ')
    .filter(Boolean)
    .map(w => w[0].toUpperCase())
    .slice(0, 2)
    .join('') || 'S';

  useEffect(() => {
    async function loadData() {
      try {
        const [p, m, mem] = await Promise.all([
          api.getLearnerProfile(),
          api.getTopicMastery(),
          api.getMemory()
        ]);
        setProfile(p);
        setMasteries(m);
        setMemoryData(mem);

        const targetConcept = m.length > 0 ? m[0].concept_name : undefined;
        const pred = await api.getPredictions(targetConcept);
        setPredictions(pred);
      } catch (e) {
        console.error("Failed to load profile:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Your Learning Profile & Mastery</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Real-time mastery tracking, smart recommendations, and your learning milestones.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Student Behavioral Identity & ML Predictions */}
        <div className="space-y-6">
          {/* Identity Card */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-sky-50 dark:bg-sky-950/60 border border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-300 flex items-center justify-center font-bold text-base shadow-xs">
                {initials}
              </div>
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">{studentName}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Active Student Profile</p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Profile Status:</span>
                <span className="font-bold text-sky-700 dark:text-sky-300 uppercase">{profile?.status || "Getting Started"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Overall Mastery:</span>
                <span className="font-bold text-slate-900 dark:text-white">{Math.round((profile?.overall_mastery || 0) * 100)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Total Study Time:</span>
                <span className="font-bold text-slate-900 dark:text-white">{profile ? Math.round(profile.total_active_study_minutes) : 0} mins</span>
              </div>
            </div>
          </div>

          {/* AI Study Forecast & Progress Insights */}
          {predictions && (
            <div className="rounded-2xl border border-sky-200 dark:border-sky-800 bg-sky-50/40 dark:bg-sky-950/30 p-6 shadow-xs space-y-4">
              <div className="flex items-center gap-2 text-sky-900 dark:text-sky-200 font-bold text-sm">
                <Cpu className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                <span>AI Study Forecast & Progress Insights</span>
              </div>

              {/* Topic Readiness */}
              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-sky-200/80 dark:border-sky-800/80 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-700 dark:text-slate-300">Topic Readiness:</span>
                  <span className="text-[10px] font-semibold text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/80 px-2 py-0.5 rounded border border-sky-200 dark:border-sky-800">Smart Assessment</span>
                </div>
                <div className="text-xs font-semibold text-sky-700 dark:text-sky-300 capitalize">
                  Current Level: {predictions.readiness_classification?.prediction?.replace(/_/g, ' ')}
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Confidence: {Math.round(predictions.readiness_classification?.confidence * 100)}%
                </div>
              </div>

              {/* Study Pace Forecast */}
              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-sky-200/80 dark:border-sky-800/80 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-700 dark:text-slate-300">Study Pace & Goals:</span>
                  <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">Pace Forecast</span>
                </div>
                <div className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                  Expected Quiz Score: {predictions.time_to_mastery_regression?.predicted_quiz_score}%
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-300">
                  Est. Minutes to 80% Mastery: ~{predictions.time_to_mastery_regression?.estimated_minutes_to_target} mins
                </div>
              </div>
            </div>
          )}

          {/* Behavior Profile */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-3">
            <h3 className="font-bold text-slate-900 dark:text-white text-sm">Learning Behavior Profile</h3>
            <div className="text-xs text-slate-600 dark:text-slate-300 space-y-2">
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-400 dark:text-slate-500">Explanation Style:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">Balanced Scaffolded</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-400 dark:text-slate-500">Conceptual Approach:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">Analogies First</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400 dark:text-slate-500">Review Frequency:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">Every 4-5 days</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Skill Mastery Table & Key Learning Moments */}
        <div className="lg:col-span-2 space-y-6">
          {/* Concept Mastery Table */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-4">
            <h2 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-sky-600 dark:text-sky-400" />
              Topic & Skill Mastery Progress
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">
                    <th className="pb-3">Concept Name</th>
                    <th className="pb-3">Mastery Level</th>
                    <th className="pb-3">Confidence</th>
                    <th className="pb-3">Questions Practiced</th>
                    <th className="pb-3">Accuracy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {masteries.map((m) => (
                    <tr key={m.id || m.concept_name} className="py-2.5">
                      <td className="py-3 font-semibold text-slate-900 dark:text-white">{m.concept_name}</td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded font-bold border ${
                          m.mastery_score >= 70 ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800' :
                          m.mastery_score >= 45 ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800' : 'bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
                        }`}>
                          {m.mastery_score}%
                        </span>
                      </td>
                      <td className="py-3 font-medium text-slate-600 dark:text-slate-300">{m.confidence}%</td>
                      <td className="py-3 text-slate-600 dark:text-slate-300">{m.evidence_count} questions</td>
                      <td className="py-3 text-slate-600 dark:text-slate-300">
                        {m.correct_count} / {m.evidence_count || 1}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Learning Milestones & Moments */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-4">
            <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
              <History className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              Key Learning Moments & Milestones
            </h3>

            <div className="space-y-3">
              {memoryData?.learning_episodes && memoryData.learning_episodes.length > 0 ? (
                memoryData.learning_episodes.map((ep: any) => (
                  <div key={ep.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-900 dark:text-white">{ep.concept}</span>
                      <span className="text-slate-400 dark:text-slate-500">{ep.date}</span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300">{ep.evidence}</p>
                    <div className="pt-1">
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950/70 text-purple-800 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                        {ep.event_type}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
                  No study milestones or difficulty alerts recorded yet.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
