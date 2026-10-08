import React, { useState, useEffect } from 'react';
import { 
  Network, 
  ArrowDown, 
  BookOpen, 
  ChevronRight, 
  Sparkles,
  Link2,
  FolderOpen
} from 'lucide-react';
import { api, getActiveCourseId, setActiveCourseId } from '../../services/api';

export const KnowledgeExplorer: React.FC = () => {
  const [courses, setCourses] = useState<any[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>(() => getActiveCourseId());
  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [] });
  const [selectedConcept, setSelectedConcept] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadInitialData() {
      try {
        const cList = await api.listCourses();
        setCourses(cList);
        if (cList.length > 0) {
          const stored = getActiveCourseId() || selectedCourseId;
          const found = cList.find(c => c.id === stored);
          const activeId = found ? found.id : cList[0].id;
          setSelectedCourseId(activeId);
          setActiveCourseId(activeId);
          await loadCourseGraph(activeId);
        }
      } catch (e) {
        console.error("Failed to load courses:", e);
      } finally {
        setLoading(false);
      }
    }
    loadInitialData();
  }, []);

  async function loadCourseGraph(courseId: string) {
    setLoading(true);
    try {
      const data = await api.getKnowledgeGraph(courseId);
      setGraphData(data);
      if (data.nodes && data.nodes.length > 0) {
        setSelectedConcept(data.nodes[0]);
      } else {
        setSelectedConcept(null);
      }
    } catch (e) {
      console.error("Failed to load knowledge graph:", e);
      setGraphData({ nodes: [], edges: [] });
      setSelectedConcept(null);
    } finally {
      setLoading(false);
    }
  }

  const handleCourseChange = (courseId: string) => {
    setSelectedCourseId(courseId);
    setActiveCourseId(courseId);
    loadCourseGraph(courseId);
  };

  const selectedCourse = courses.find(c => c.id === selectedCourseId);
  const nodes = graphData.nodes || [];

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Header with Course Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Curriculum Knowledge Graph</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Topological concept hierarchy, prerequisite dependency DAG, and pedagogical progression.
          </p>
        </div>

        {courses.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Active Course:</span>
            <select
              value={selectedCourseId}
              onChange={(e) => handleCourseChange(e.target.value)}
              className="px-3.5 py-2 text-sm font-semibold rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 shadow-2xs focus:outline-sky-500"
            >
              {courses.map(c => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {courses.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12 text-center space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center">
            <Network className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">No Knowledge Graph Available</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              You haven't added any courses yet. Add your first course or upload materials to generate an automated prerequisite concept DAG.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Prerequisite Learning Chain */}
          <div className="lg:col-span-2 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h2 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
                <Network className="w-5 h-5 text-sky-600 dark:text-sky-400" />
                Prerequisite Learning Progression (Topological DAG)
              </h2>
              <span className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                {nodes.length} Concepts Mapped
              </span>
            </div>

            {/* Concept Nodes List */}
            {nodes.length === 0 ? (
              <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-xs space-y-2">
                <p>No concepts extracted for {selectedCourse?.title || "this course"} yet.</p>
                <p className="text-slate-500 dark:text-slate-400">
                  Upload textbooks, lecture slides, or lecture videos in the Course Library to extract knowledge units.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {nodes.map((node: any, idx: number, arr: any[]) => (
                  <React.Fragment key={node.id}>
                    <div
                      onClick={() => setSelectedConcept(node)}
                      className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center justify-between group ${
                        (selectedConcept?.id && selectedConcept.id === node.id) ||
                        (selectedConcept?.name && selectedConcept.name === (node.name || node.label))
                          ? 'border-sky-500 bg-sky-50/70 dark:bg-sky-950/60 shadow-2xs'
                          : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 bg-white dark:bg-slate-900'
                      }`}
                    >
                      <div className="flex items-center gap-3.5">
                        <span className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800 group-hover:bg-sky-100 dark:group-hover:bg-sky-950 text-slate-700 dark:text-slate-300 group-hover:text-sky-700 dark:group-hover:text-sky-300 flex items-center justify-center font-bold text-xs border border-slate-200 dark:border-slate-700">
                          {idx + 1}
                        </span>
                        <div>
                          <h4 className="text-sm font-bold text-slate-900 dark:text-white">{node.name || node.label || `Concept ${idx + 1}`}</h4>
                          <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-md">
                            {node.summary || node.definition || (node.topic_title ? `Core topic under ${node.topic_title}` : `Key concept unit in ${selectedCourse?.title || 'the curriculum'}.`)}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize border ${
                          (node.difficulty_level || node.difficulty) === 'hard' ? 'bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border-red-200 dark:border-red-900/40' :
                          (node.difficulty_level || node.difficulty) === 'medium' ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-900/40' : 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900/40'
                        }`}>
                          {node.difficulty_level || node.difficulty || 'medium'}
                        </span>
                        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-sky-600 dark:group-hover:text-sky-400 group-hover:translate-x-0.5 transition-transform" />
                      </div>
                    </div>

                    {idx < arr.length - 1 && (
                      <div className="flex justify-center -my-1 text-slate-300 dark:text-slate-700">
                        <ArrowDown className="w-4 h-4" />
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Selected Concept Detail Inspector */}
          <div className="space-y-6">
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-sky-700 dark:text-sky-300">
                <BookOpen className="w-4 h-4" />
                <span>Concept Inspector</span>
              </div>

              {selectedConcept ? (
                <>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    {selectedConcept.name || selectedConcept.label || "Concept Overview"}
                  </h3>

                  <div className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-sans space-y-2">
                    <p>
                      {selectedConcept.summary || selectedConcept.definition || 
                        `Fundamental concept in ${selectedCourse?.title || 'the course curriculum'} establishing core mechanisms and learning outcomes.`}
                    </p>
                  </div>

                  <div className="space-y-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500 dark:text-slate-400">Domain Topic:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedConcept.topic_title || selectedCourse?.subject || "Core Curriculum"}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500 dark:text-slate-400">Difficulty Level:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200 capitalize">{selectedConcept.difficulty_level || selectedConcept.difficulty || "Medium"}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-500 dark:text-slate-400">Linked Course:</span>
                      <span className="font-semibold text-sky-700 dark:text-sky-300">{selectedCourse?.title || "Active Course"}</span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-xs">
                  Select a concept node from the learning progression to inspect its details and prerequisite connections.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
