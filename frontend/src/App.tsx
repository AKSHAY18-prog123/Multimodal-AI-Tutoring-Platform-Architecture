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
  const [assessmentConfig, setAssessmentConfig] = useState<{ is_diagnostic?: boolean; course_id?: string }>({});
  
  // Student identification state
  const [currentUser, setCurrentUser] = useState<{ id: string; name: string } | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showCreateCourse, setShowCreateCourse] = useState(false);
  const [checkingUser, setCheckingUser] = useState(true);
  const [courseRefreshKey, setCourseRefreshKey] = useState(0);
  const [lastCreatedCourseId, setLastCreatedCourseId] = useState<string | undefined>(undefined);

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
    setCourseRefreshKey(prev => prev + 1);
    if (course?.id) {
      setLastCreatedCourseId(course.id);
    }
    setShowCreateCourse(false);
    if (meta?.startDiagnostic) {
      setAssessmentConfig({ is_diagnostic: true, course_id: course?.id });
      setCurrentTab('assessments');
    } else {
      setCurrentTab('courses');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors duration-200">
      <Navbar 
        currentTab={currentTab} 
        onTabChange={(tab) => handleNavigate(tab)} 
        studentName={currentUser?.name || getActiveUserName()}
        isColdStart={false}
      />

      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-12">
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
          <Courses 
            onOpenAddCourse={() => setShowCreateCourse(true)}
            activeCourseId={lastCreatedCourseId}
            refreshTrigger={courseRefreshKey}
          />
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
