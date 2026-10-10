import React from 'react';
import { 
  LayoutDashboard, 
  MessageSquare, 
  CheckSquare, 
  FolderOpen, 
  UserCircle, 
  Sparkles,
  BookOpen,
  Sun,
  Moon
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

interface NavbarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  isColdStart?: boolean;
  studentName?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ 
  currentTab, 
  onTabChange, 
  isColdStart = false, 
  studentName = "Student" 
}) => {
  const { theme, toggleTheme } = useTheme();

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'tutor', label: 'Tutor Chat', icon: MessageSquare },
    { id: 'assessments', label: 'Adaptive Tests', icon: CheckSquare },
    { id: 'courses', label: 'Course Library', icon: FolderOpen },
    { id: 'profile', label: 'Learner Profile', icon: UserCircle },
  ];

  const initials = studentName
    .split(' ')
    .filter(Boolean)
    .map(w => w[0].toUpperCase())
    .slice(0, 2)
    .join('') || 'ST';

  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200/90 dark:border-slate-800 shadow-xs w-full transition-colors duration-200">
      <div className="w-full px-3 sm:px-5 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-3">
          
          {/* Logo & Brand */}
          <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 via-sky-500 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-sky-500/20 shrink-0">
              <BookOpen className="w-5 h-5 shrink-0" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-base sm:text-lg font-bold text-slate-900 dark:text-white tracking-tight whitespace-nowrap">
                  SynapseTutor
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-sky-50 dark:bg-sky-950/70 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800 uppercase tracking-wider shrink-0">
                  Track D
                </span>
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap hidden 2xl:block">
                Adaptive Multimodal Learning Platform
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center justify-start xl:justify-center gap-1 xl:gap-1.5 flex-1 min-w-0 overflow-x-auto no-scrollbar py-1 px-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`flex items-center gap-1.5 lg:gap-2 px-2.5 xl:px-3.5 py-1.5 xl:py-2 text-xs xl:text-sm font-semibold rounded-xl whitespace-nowrap shrink-0 transition-all duration-150 cursor-pointer ${
                    isActive
                      ? 'bg-sky-50 dark:bg-sky-950/70 text-sky-700 dark:text-sky-300 shadow-xs border border-sky-200 dark:border-sky-800 font-bold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/80 dark:hover:bg-slate-800/80 border border-transparent'
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-sky-600 dark:text-sky-400' : 'text-slate-400 dark:text-slate-500'}`} />
                  <span className="whitespace-nowrap">{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Controls: Theme Toggle & User Profile */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            
            {/* Dark/Light Mode Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200/80 dark:border-slate-800 transition-all duration-150 cursor-pointer shadow-2xs"
              title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <Sun className="w-4 h-4 text-amber-400 animate-in spin-in-90 duration-300" />
              ) : (
                <Moon className="w-4 h-4 text-slate-700 animate-in spin-in-90 duration-300" />
              )}
            </button>

            {/* Learner Model Status Badge */}
            {isColdStart ? (
              <span className="hidden xl:inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 shrink-0">
                <Sparkles className="w-3.5 h-3.5 text-amber-500 animate-pulse shrink-0" />
                Uncalibrated
              </span>
            ) : (
              <span className="hidden xl:inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 shrink-0 whitespace-nowrap">
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                Active Model
              </span>
            )}
            
            {/* Student Avatar */}
            <div className="flex items-center gap-2 pl-2 sm:pl-3 border-l border-slate-200 dark:border-slate-800 shrink-0">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-sky-100 to-indigo-100 dark:from-sky-950 dark:to-indigo-950 text-sky-800 dark:text-sky-300 border border-sky-200 dark:border-sky-800 flex items-center justify-center font-bold text-xs shadow-xs shrink-0">
                {initials}
              </div>
              <div className="hidden lg:flex flex-col text-left">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 leading-tight whitespace-nowrap">{studentName}</span>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">Student</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </header>
  );
};
