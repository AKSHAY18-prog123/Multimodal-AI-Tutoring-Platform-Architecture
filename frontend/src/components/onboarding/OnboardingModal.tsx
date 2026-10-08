import React, { useState } from 'react';
import { BookOpen, Sparkles, ArrowRight, User } from 'lucide-react';
import { api, setActiveUser } from '../../services/api';

interface OnboardingModalProps {
  onComplete: (user: { id: string; name: string }) => void;
}

export const OnboardingModal: React.FC<OnboardingModalProps> = ({ onComplete }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = name.trim();
    if (!cleanName) {
      setError('Please provide your name to set up your learning space.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const res = await api.onboardUser({
        name: cleanName,
        email: email.trim() || undefined
      });
      setActiveUser(res.id, res.name);
      onComplete({ id: res.id, name: res.name });
    } catch (err: any) {
      setError(err.message || 'Onboarding failed. Please try again.');
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-md p-4 animate-fade-in">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden transform transition-all">
        {/* Header Banner */}
        <div className="bg-gradient-to-tr from-brand-700 via-brand-600 to-sky-600 px-8 pt-8 pb-6 text-white text-center">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center mb-4 shadow-inner">
            <BookOpen className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight">Welcome to SynapseTutor</h2>
          <p className="text-brand-100 text-xs mt-1">
            Personalized Multimodal AI Learning & Adaptive Tutoring
          </p>
        </div>

        {/* Form Body */}
        <div className="p-8 space-y-6">
          <div className="text-center space-y-1">
            <h3 className="text-base font-semibold text-slate-900">Let's set up your profile</h3>
            <p className="text-xs text-slate-500">
              We'll tailor the explanations, knowledge tracking, and pace specifically to you.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                What should we call you? *
              </label>
              <div className="relative">
                <User className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
                <input
                  type="text"
                  required
                  autoFocus
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 text-slate-900 font-medium placeholder-slate-400"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Email Address <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="alex.student@university.edu"
                className="w-full px-4 py-2.5 text-sm bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 text-slate-900 placeholder-slate-400"
              />
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !name.trim()}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold text-sm shadow-md transition-all flex items-center justify-center gap-2 group cursor-pointer"
            >
              <span>{submitting ? 'Setting up workspace...' : 'Continue'}</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>

          <div className="flex items-center gap-2 justify-center text-[11px] text-slate-400">
            <Sparkles className="w-3.5 h-3.5 text-brand-500" />
            <span>Zero fake data • Starts in clean baseline state</span>
          </div>
        </div>
      </div>
    </div>
  );
};
