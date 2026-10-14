import { useEffect, useRef, useState, useCallback } from 'react';
import { api, getActiveUserId } from '../services/api';

const IDLE_TIMEOUT_MS = 120_000; // 2 minutes without user interaction = idle
const SYNC_INTERVAL_SEC = 30;    // Sync with backend every 30 seconds
const INITIAL_SYNC_THRESHOLD_SEC = 10; // First sync after 10 seconds for immediate feedback

export function useStudyTimeTracker(currentTab: string) {
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [isIdle, setIsIdle] = useState(false);

  const pendingSecondsRef = useRef(0);
  const lastActiveRef = useRef(Date.now());
  const hasSyncedOnceRef = useRef(false);
  const currentTabRef = useRef(currentTab);
  const isSyncingRef = useRef(false);

  useEffect(() => {
    currentTabRef.current = currentTab;
  }, [currentTab]);

  const getActivityType = useCallback((tab: string): string => {
    if (tab === 'tutor' || tab === 'courses') return 'reading';
    if (tab === 'assessments') return 'problem_solving';
    return 'general';
  }, []);

  const syncStudyTime = useCallback(async (secondsToSync: number, activityType: string) => {
    if (secondsToSync <= 0 || isSyncingRef.current) return;
    const userId = getActiveUserId();
    if (!userId) return;

    try {
      isSyncingRef.current = true;
      const res = await api.syncStudyTime({
        seconds_added: secondsToSync,
        activity_type: activityType,
        user_id: userId
      });

      if (res) {
        window.dispatchEvent(new CustomEvent('study-time-updated', { detail: res }));
      }
    } catch (err) {
      console.warn('Study time heartbeat sync failed:', err);
      // Put unsynced seconds back
      pendingSecondsRef.current += secondsToSync;
    } finally {
      isSyncingRef.current = false;
    }
  }, []);

  // Listen to user interaction to reset idle timer
  useEffect(() => {
    const markActive = () => {
      lastActiveRef.current = Date.now();
      setIsIdle(false);
    };

    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    events.forEach(evt => window.addEventListener(evt, markActive, { passive: true }));

    return () => {
      events.forEach(evt => window.removeEventListener(evt, markActive));
    };
  }, []);

  // Main active tracking loop
  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      const isVisible = document.visibilityState === 'visible';
      const userActive = (now - lastActiveRef.current) < IDLE_TIMEOUT_MS;

      if (!userActive) {
        setIsIdle(true);
      }

      if (isVisible && userActive) {
        pendingSecondsRef.current += 1;
        setSessionSeconds(prev => prev + 1);

        const threshold = hasSyncedOnceRef.current ? SYNC_INTERVAL_SEC : INITIAL_SYNC_THRESHOLD_SEC;

        if (pendingSecondsRef.current >= threshold) {
          const toSync = pendingSecondsRef.current;
          pendingSecondsRef.current = 0;
          hasSyncedOnceRef.current = true;
          syncStudyTime(toSync, getActivityType(currentTabRef.current));
        }
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [getActivityType, syncStudyTime]);

  // Sync remaining time on page unload or visibility hide
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden' && pendingSecondsRef.current >= 5) {
        const toSync = pendingSecondsRef.current;
        pendingSecondsRef.current = 0;
        syncStudyTime(toSync, getActivityType(currentTabRef.current));
      }
    };

    const handleBeforeUnload = () => {
      if (pendingSecondsRef.current >= 5) {
        const toSync = pendingSecondsRef.current;
        pendingSecondsRef.current = 0;
        const uid = getActiveUserId();
        if (uid && navigator.sendBeacon) {
          const payload = JSON.stringify({
            seconds_added: toSync,
            activity_type: getActivityType(currentTabRef.current),
            user_id: uid
          });
          const blob = new Blob([payload], { type: 'application/json' });
          navigator.sendBeacon('/api/v1/learner/study-time', blob);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [getActivityType, syncStudyTime]);

  return { sessionSeconds, isIdle };
}
