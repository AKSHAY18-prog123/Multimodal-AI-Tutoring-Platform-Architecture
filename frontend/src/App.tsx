import React, { useState, useEffect } from 'react';
import { Navbar } from './components/layout/Navbar';
import { Dashboard } from './pages/Dashboard/Dashboard';
import { Tutor } from './pages/Tutor/Tutor';
import { Assessments } from './pages/Assessments/Assessments';
import { KnowledgeExplorer } from './pages/KnowledgeExplorer/KnowledgeExplorer';
import { Courses } from './pages/Courses/Courses';
import { LearnerProfile } from './pages/LearnerProfile/LearnerProfile';
import { Analytics } from './pages/Analytics/Analytics';
import { OnboardingModal } from './components/onboarding/OnboardingModal';
import { CreateCourseModal } from './components/courses/CreateCourseModal';
import { api, getActiveUserId, getActiveUserName, setActiveUser } from './services/api';

export function App() {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [assessmentConfig, setAssessmentConfig] = useState<{ is_diagnostic?: boolean }>({});
  
  // Student identification state
  const [currentUser, setCurrentUser] = useState<{ id: string; name: string } | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showCreateCourse, setShowCreateCourse] = useState(false);
  const [checkingUser, setCheckingUser] = useState(true);

  // Check if student profile exists on startup
  useEffect(() => {
    async function checkStudentStatus() {
      try {
        const storedId = getActiveUserId();
        const status = await api.getUserStatus(storedId || undefined);
        
        if (status.exists && status.user && status.onboarding_completed) {
          setActiveUser(status.user.id, status.user.name);
          setCurrentUser({ id: status.user.id, name: status.user.name });
          setShowOnboarding(false);
        } else {
          // Brand new student or incomplete onboarding
          setShowOnboarding(true);
        }
      } catch (err) {
        console.warn("Could not reach backend or no users:", err);
        // Default to onboarding prompt if no active user
        if (!getActiveUserId()) {
          setShowOnboarding(true);
        } else {
          setCurrentUser({ id: getActiveUserId(), name: getActiveUserName() });
        }
      } finally {
        setCheckingUser(false);
      }
    }
    checkStudentStatus();
  }, []);

  const handleOnboardComplete = (user: { id: string; name: string }) => {
    setCurrentUser(user);
    setShowOnboarding(false);
    setCurrentTab('dashboard');
  };

  const handleNavigate = (tab: string, meta?: any) => {
    if (tab === 'assessments' && meta) {
      setAssessmentConfig(meta);
    }
    if (tab === 'create_course') {
      setShowCreateCourse(true);
      return;
    }
    setCurrentTab(tab);
  };

  const handleCourseCreated = (course: any, meta?: { startDiagnostic?: boolean }) => {
    if (meta?.startDiagnostic) {
      setAssessmentConfig({ is_diagnostic: true });
      setCurrentTab('assessments');
    } else {
      setCurrentTab('courses');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar 
        currentTab={currentTab} 
        onTabChange={(tab) => handleNavigate(tab)} 
        studentName={currentUser?.name || getActiveUserName()}
        isColdStart={false}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {currentTab === 'dashboard' && (
          <Dashboard 
            onNavigate={handleNavigate} 
            onOpenAddCourse={() => setShowCreateCourse(true)}
          />
        )}
        {currentTab === 'tutor' && <Tutor />}
        {currentTab === 'assessments' && <Assessments initialDiagnostic={assessmentConfig.is_diagnostic} />}
        {currentTab === 'explorer' && <KnowledgeExplorer />}
        {currentTab === 'courses' && (
          <Courses onOpenAddCourse={() => setShowCreateCourse(true)} />
        )}
        {currentTab === 'profile' && <LearnerProfile />}
        {currentTab === 'analytics' && <Analytics />}
      </main>

      {/* First-Time User Onboarding Modal */}
      {showOnboarding && !checkingUser && (
        <OnboardingModal onComplete={handleOnboardComplete} />
      )}

      {/* Add Course / Resource Modal */}
      <CreateCourseModal
        isOpen={showCreateCourse}
        onClose={() => setShowCreateCourse(false)}
        onCourseCreated={handleCourseCreated}
      />
    </div>
  );
}

export default App;
