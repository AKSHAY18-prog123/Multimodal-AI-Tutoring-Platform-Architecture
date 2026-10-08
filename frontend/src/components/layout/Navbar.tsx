import React from 'react';
import { 
  LayoutDashboard, 
  MessageSquare, 
  CheckSquare, 
  Network, 
  FolderOpen, 
  UserCircle, 
  TrendingUp, 
  Sparkles,
  BookOpen
} from 'lucide-react';

interface NavbarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  isColdStart?: boolean;
  studentName?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onTabChange, isColdStart, studentName = "Student" }) => {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'tutor', label: 'Tutor Chat', icon: MessageSquare },
    { id: 'assessments', label: 'Adaptive Tests', icon: CheckSquare },
    { id: 'explorer', label: 'Knowledge Explorer', icon: Network },
    { id: 'courses', label: 'Course Library', icon: FolderOpen },
    { id: 'profile', label: 'Learner Profile', icon: UserCircle },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp },
  ];

  const initials = studentName
    .split(' ')
    .filter(Boolean)
    .map(w => w[0].toUpperCase())
    .slice(0, 2)
    .join('') || 'S';

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo & Product Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-700 to-sky-500 flex items-center justify-center text-white shadow-md">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <span className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-1.5">
                SynapseTutor <span className="text-xs font-semibold px-2 py-0.5 rounded bg-brand-50 text-brand-700 border border-brand-200">Track D</span>
              </span>
              <p className="text-xs text-slate-500 font-medium -mt-0.5">Adaptive Multimodal Learning Platform</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex space-x-1 lg:space-x-2 my-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg transition-all ${
                    isActive
                      ? 'bg-slate-100 text-brand-700 font-semibold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-brand-600' : 'text-slate-400'}`} />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* User Profile / Baseline Badge */}
          <div className="flex items-center space-x-3">
            {isColdStart ? (
              <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                <Sparkles className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
                Uncalibrated Baseline
              </span>
            ) : (
              <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Active Learner Model
              </span>
            )}
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
              <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 border border-brand-200 flex items-center justify-center font-bold text-xs">
                {initials}
              </div>
              <span className="text-xs font-semibold text-slate-800 hidden lg:inline">{studentName}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
