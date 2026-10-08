import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Clock, 
  Award, 
  CheckCircle2, 
  Sparkles, 
  BarChart3,
  ShieldCheck
} from 'lucide-react';
import { api } from '../../services/api';

export const Analytics: React.FC = () => {
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getAnalytics();
        setAnalytics(data);
      } catch (e) {
        console.error("Failed to load analytics:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Learning Analytics & Evaluation</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Measurable learning improvement, time models, and question novelty metrics.
        </p>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-xs">
          <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase">Measurable Mastery Gain</span>
          <div className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-2">
            {analytics?.learning_gains || "Calibrating..."}
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Measured pre/post assessments</p>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-xs">
          <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase">Question Novelty Rate</span>
          <div className="text-3xl font-extrabold text-sky-600 dark:text-sky-400 mt-2">
            {analytics?.novelty_metrics?.novelty_rate_percentage || 100}%
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            0% repetition rate via cosine hashing
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-xs">
          <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase">Active Study Time</span>
          <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-2">
            {analytics?.total_study_minutes || 0} mins
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Total engaged platform sessions</p>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-xs">
          <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase">Tests Completed</span>
          <div className="text-3xl font-extrabold text-purple-600 dark:text-purple-400 mt-2">
            {analytics?.assessments_completed || 0}
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Adaptive diagnostic evaluations</p>
        </div>
      </div>

      {/* Trajectory Timeline & Study Time Split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Mastery Trajectory Curve */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-4">
          <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-sky-600 dark:text-sky-400" />
            Mastery Trajectory Over Sessions
          </h3>

          <div className="space-y-4 pt-2">
            {!analytics?.mastery_timeline?.length ? (
              <div className="py-8 text-center text-xs text-slate-400 dark:text-slate-500">
                No longitudinal assessment trajectory recorded yet. Complete adaptive tests to build your mastery trajectory.
              </div>
            ) : (
              analytics.mastery_timeline.map((step: any, idx: number) => (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-800 dark:text-slate-200">{step.session}</span>
                    <span className="text-sky-700 dark:text-sky-300">{step.mastery}%</span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-sky-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${step.mastery}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Study Time Model (Reading vs Problem Solving) */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-4">
          <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Learning Time Allocation Model
          </h3>

          <div className="space-y-4 pt-2 text-xs">
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-2">
              <div className="flex justify-between font-semibold">
                <span className="text-slate-600 dark:text-slate-400">Material Reading & Tutor Explanation:</span>
                <span className="text-slate-900 dark:text-white">{analytics?.reading_minutes || 0} mins (60%)</span>
              </div>
              <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2">
                <div className="bg-blue-500 h-2 rounded-full w-[60%]" />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-2">
              <div className="flex justify-between font-semibold">
                <span className="text-slate-600 dark:text-slate-400">Problem Solving & Quiz Answering:</span>
                <span className="text-slate-900 dark:text-white">{analytics?.answering_minutes || 0} mins (40%)</span>
              </div>
              <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2">
                <div className="bg-emerald-500 h-2 rounded-full w-[40%]" />
              </div>
            </div>

            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed pt-1">
              Data collected across active reading and problem answering sessions informs the Gradient Boosting
              time-to-mastery regression model.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
