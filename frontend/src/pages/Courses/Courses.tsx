import React, { useState, useEffect } from 'react';
import { 
  FolderOpen, 
  Upload, 
  FileText, 
  Presentation, 
  Video, 
  Image as ImageIcon, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  Plus,
  RefreshCw,
  Trash2,
  Sparkles,
  Cpu,
  Layers,
  Zap,
  Check,
  FileUp,
  Activity
} from 'lucide-react';
import { api, getActiveCourseId, setActiveCourseId } from '../../services/api';
import { DocumentItem, Course } from '../../types';

interface CoursesProps {
  onOpenAddCourse?: () => void;
  activeCourseId?: string;
  refreshTrigger?: number;
}

export const Courses: React.FC<CoursesProps> = ({ onOpenAddCourse, activeCourseId, refreshTrigger }) => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>(() => getActiveCourseId() || activeCourseId || "");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [sourceCategory, setSourceCategory] = useState<'course_source' | 'student_provided'>('course_source');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [uploadingFiles, setUploadingFiles] = useState<string[]>([]);
  const [trashingCourse, setTrashingCourse] = useState(false);

  useEffect(() => {
    loadCourses(activeCourseId);
  }, [refreshTrigger, activeCourseId]);

  useEffect(() => {
    if (selectedCourseId) {
      loadDocuments(selectedCourseId);
    } else {
      setDocuments([]);
    }
  }, [selectedCourseId]);

  // Polling for async background ingestion progress
  useEffect(() => {
    if (!activeJobId) return;

    const interval = setInterval(async () => {
      try {
        const statusData = await api.getDocumentStatus(activeJobId);
        setUploadProgress(statusData.progress);
        setUploadStatus(statusData.status);

        if (statusData.status === 'completed' || statusData.status === 'failed') {
          setActiveJobId(null);
          setUploading(false);
          setUploadingFiles([]);
          if (selectedCourseId) loadDocuments(selectedCourseId);
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJobId, selectedCourseId]);

  async function loadCourses(preferCourseId?: string) {
    try {
      const data = await api.listCourses();
      setCourses(data);
      if (data.length > 0) {
        const savedCourse = preferCourseId || getActiveCourseId() || selectedCourseId;
        const matched = data.find(c => c.id === savedCourse);
        if (matched) {
          setSelectedCourseId(matched.id);
          setActiveCourseId(matched.id);
        } else {
          setSelectedCourseId(data[0].id);
          setActiveCourseId(data[0].id);
        }
      } else {
        setSelectedCourseId("");
        setActiveCourseId("");
        setDocuments([]);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function loadDocuments(courseId: string) {
    try {
      const docs = await api.listCourseDocuments(courseId);
      setDocuments(docs);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleTrashCourse(courseId: string) {
    const course = courses.find(c => c.id === courseId);
    const confirmed = window.confirm(
      `Move specific course "${course?.title || 'Selected Course'}" to trash?\n\nThis will only remove this specific course and its materials, while keeping your other courses intact.`
    );
    if (!confirmed) return;

    setTrashingCourse(true);
    try {
      await api.deleteCourse(courseId);
      const remaining = courses.filter(c => c.id !== courseId);
      setCourses(remaining);
      if (remaining.length > 0) {
        setSelectedCourseId(remaining[0].id);
      } else {
        setSelectedCourseId("");
        setDocuments([]);
      }
    } catch (err: any) {
      alert(`Failed to trash course: ${err.message}`);
    } finally {
      setTrashingCourse(false);
    }
  }

  async function handleTrashDocument(docId: string, filename: string) {
    const confirmed = window.confirm(`Move document "${filename}" to trash?`);
    if (!confirmed) return;

    try {
      await api.deleteDocument(docId);
      if (selectedCourseId) {
        await loadDocuments(selectedCourseId);
      }
    } catch (err: any) {
      alert(`Failed to trash document: ${err.message}`);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const fileList = Array.from(e.target.files || []);
    if (fileList.length === 0 || !selectedCourseId) return;

    setUploading(true);
    setUploadProgress(15);
    setUploadStatus("Processing files...");
    setUploadingFiles(fileList.map(f => f.name));

    try {
      const res = await api.uploadDocumentsBatch(selectedCourseId, fileList, sourceCategory);
      if (res.job_ids && res.job_ids.length > 0) {
        setActiveJobId(res.job_ids[res.job_ids.length - 1]);
      }
      setUploadProgress(35);
      setUploadStatus("extracting");
      await loadDocuments(selectedCourseId);
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
      setUploading(false);
      setUploadProgress(null);
      setUploadingFiles([]);
    }
  }

  const getDocIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'pdf': return <FileText className="w-5 h-5 text-red-500" />;
      case 'pptx': case 'ppt': return <Presentation className="w-5 h-5 text-orange-500" />;
      case 'video': case 'mp4': return <Video className="w-5 h-5 text-sky-500" />;
      default: return <ImageIcon className="w-5 h-5 text-emerald-500" />;
    }
  };

  const selectedCourse = courses.find(c => c.id === selectedCourseId);

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Course Knowledge Library</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Multimodal document ingestion, automated page/slide/timestamp indexing, and source provenance.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {courses.length > 0 && (
            <>
              <select
                value={selectedCourseId}
                onChange={(e) => {
                  setSelectedCourseId(e.target.value);
                  setActiveCourseId(e.target.value);
                }}
                className="px-3.5 py-2 text-sm font-semibold rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 shadow-2xs focus:outline-sky-500 cursor-pointer"
              >
                {courses.map(c => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
              </select>

              {selectedCourseId && (
                <button
                  onClick={() => handleTrashCourse(selectedCourseId)}
                  disabled={trashingCourse}
                  title={`Trash selected course: "${selectedCourse?.title || ''}"`}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-semibold rounded-lg bg-red-50 hover:bg-red-100 dark:bg-red-950/40 dark:hover:bg-red-900/50 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900/60 shadow-xs transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>{trashingCourse ? 'Trashing...' : 'Trash Course'}</span>
                </button>
              )}
            </>
          )}
          <button
            onClick={onOpenAddCourse}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-semibold rounded-lg bg-sky-600 hover:bg-sky-700 text-white shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Add Course
          </button>
        </div>
      </div>

      {courses.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12 text-center space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center">
            <FolderOpen className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Your Knowledge Library is Empty</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              Add your first course and upload course materials (PDF, PPTX, Video, Images) to start multimodal indexing.
            </p>
          </div>
          <button
            onClick={onOpenAddCourse}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-600 text-white font-bold text-sm shadow-sm hover:bg-sky-700 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Add Course / Resource
          </button>
        </div>
      ) : (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Multimodal Upload Zone */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 backdrop-blur-md p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-gradient-to-tr from-sky-500/20 via-indigo-500/20 to-purple-500/20 text-sky-500 dark:text-sky-400 border border-sky-500/30 shadow-xs">
                <Upload className="w-4 h-4" />
              </div>
              <span>Upload Materials</span>
            </h2>
            <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-sky-500" />
              AI-Indexed
            </span>
          </div>

          {/* Source Category Selector */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Source Provenance
            </label>
            <div className="grid grid-cols-2 gap-2 text-xs font-semibold p-1 rounded-xl bg-slate-100 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setSourceCategory('course_source')}
                className={`py-2 px-3 rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  sourceCategory === 'course_source'
                    ? 'bg-white dark:bg-slate-800 text-sky-600 dark:text-sky-400 shadow-xs font-bold border border-slate-200/80 dark:border-slate-700'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                <span>📘 Official Source</span>
              </button>
              <button
                type="button"
                onClick={() => setSourceCategory('student_provided')}
                className={`py-2 px-3 rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  sourceCategory === 'student_provided'
                    ? 'bg-white dark:bg-slate-800 text-sky-600 dark:text-sky-400 shadow-xs font-bold border border-slate-200/80 dark:border-slate-700'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                <span>📝 Personal Note</span>
              </button>
            </div>
          </div>

          {/* Dropzone & Dynamic Ingestion Container */}
          <div className={`relative overflow-hidden rounded-2xl border-2 transition-all duration-300 ${
            uploading
              ? 'border-sky-500/60 bg-gradient-to-b from-sky-950/30 via-slate-900/60 to-slate-950/80 shadow-lg shadow-sky-500/10 p-6'
              : 'border-dashed border-slate-300 dark:border-slate-700/80 hover:border-sky-500 bg-slate-50/50 dark:bg-slate-950/40 hover:bg-sky-50/20 dark:hover:bg-sky-950/20 p-7 text-center cursor-pointer group'
          }`}>
            <input
              type="file"
              multiple
              onChange={handleFileUpload}
              disabled={uploading}
              className="absolute inset-0 opacity-0 cursor-pointer z-10"
              accept=".pdf,.pptx,.ppt,.mp4,.webm,.png,.jpg,.jpeg,.mp3,.wav"
            />

            {!uploading ? (
              /* Idle State */
              <div className="flex flex-col items-center space-y-3 pointer-events-none">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-sky-500/15 via-indigo-500/15 to-purple-500/15 group-hover:from-sky-500/25 group-hover:to-purple-500/25 border border-sky-500/30 flex items-center justify-center text-sky-500 dark:text-sky-400 transition-all duration-300 group-hover:scale-110 shadow-xs">
                  <FileUp className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-bold text-slate-800 dark:text-slate-200 group-hover:text-sky-500 dark:group-hover:text-sky-400 transition-colors">
                    Click or Drag Lecture Files Here
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 max-w-[260px] mx-auto leading-relaxed">
                    Upload multiple files simultaneously for automated vision extraction & indexing.
                  </p>
                </div>
                {/* Supported Format Badges */}
                <div className="flex flex-wrap gap-1.5 justify-center pt-2">
                  {['PDF', 'PPTX', 'MP4', 'Audio', 'Images'].map((fmt) => (
                    <span key={fmt} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-200/70 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 border border-slate-300/50 dark:border-slate-700">
                      {fmt}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              /* Active Uploading / Processing State */
              <div className="space-y-5">
                {/* Active Ingestion Header */}
                <div className="flex items-center justify-between pb-3 border-b border-sky-900/40">
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-sky-500"></span>
                    </span>
                    <span className="text-xs font-bold text-sky-400 uppercase tracking-wide">
                      AI Ingestion Active
                    </span>
                  </div>
                  <span className="text-xs font-mono font-bold text-sky-300 bg-sky-950/80 px-2 py-0.5 rounded border border-sky-800">
                    {uploadingFiles.length} file(s)
                  </span>
                </div>

                {/* Animated File Chips */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Current Batch
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {uploadingFiles.map((fn, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-lg bg-sky-950/60 text-sky-200 border border-sky-500/40 font-mono shadow-xs animate-pulse">
                        <FileText className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                        <span className="truncate max-w-[150px]">{fn}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 4-Stage Interactive Pipeline Stepper */}
                <div className="space-y-2 pt-1">
                  <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400">
                    <span>Pipeline Progress</span>
                    <span className="text-sky-400 font-bold">{uploadProgress ?? 10}%</span>
                  </div>
                  
                  {/* Stepper Grid */}
                  <div className="grid grid-cols-4 gap-1.5 text-center">
                    {[
                      { id: 1, label: 'Upload', icon: Upload, minPct: 0 },
                      { id: 2, label: 'Vision OCR', icon: Layers, minPct: 25 },
                      { id: 3, label: 'Chunking', icon: Cpu, minPct: 55 },
                      { id: 4, label: 'Embed Graph', icon: Zap, minPct: 80 }
                    ].map(step => {
                      const cur = uploadProgress ?? 10;
                      const isComplete = cur > step.minPct + 20;
                      const isActive = cur >= step.minPct && cur <= step.minPct + 25;
                      const StepIcon = step.icon;

                      return (
                        <div
                          key={step.id}
                          className={`p-2 rounded-xl border flex flex-col items-center gap-1 transition-all ${
                            isComplete
                              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                              : isActive
                              ? 'bg-sky-950/80 border-sky-500 text-sky-200 shadow-xs shadow-sky-500/20 scale-[1.03]'
                              : 'bg-slate-900/40 border-slate-800 text-slate-500'
                          }`}
                        >
                          <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                            isComplete ? 'bg-emerald-500 text-white' : isActive ? 'bg-sky-500 text-white animate-bounce' : 'bg-slate-800 text-slate-400'
                          }`}>
                            {isComplete ? <Check className="w-3 h-3" /> : <StepIcon className="w-3 h-3" />}
                          </div>
                          <span className="text-[9px] font-bold leading-tight truncate w-full">{step.label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Shimmering Progress Bar */}
                <div className="space-y-2">
                  <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden border border-slate-700/60 relative">
                    <div
                      className="bg-gradient-to-r from-sky-400 via-indigo-500 to-purple-500 h-full rounded-full transition-all duration-300 relative overflow-hidden"
                      style={{ width: `${uploadProgress ?? 15}%` }}
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
                    </div>
                  </div>
                </div>

                {/* Live Activity Status Feed */}
                <div className="p-3 rounded-xl bg-slate-950/90 border border-slate-800/80 text-[11px] flex items-center gap-2.5 text-slate-300 font-mono">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-400 shrink-0" />
                  <span className="truncate">
                    {(uploadProgress ?? 0) < 25
                      ? "Uploading streams & verifying schemas..."
                      : (uploadProgress ?? 0) < 55
                      ? "Multimodal OCR extracting slides, formulas & diagrams..."
                      : (uploadProgress ?? 0) < 85
                      ? "Partitioning tokens into semantic concept chunks..."
                      : "Generating dense vector embeddings & knowledge graph nodes..."}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Ingested Document Inventory */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xs space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h2 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-sky-600 dark:text-sky-400" />
              Indexed Documents & Sources ({documents.length})
            </h2>
            <button
              onClick={() => selectedCourseId && loadDocuments(selectedCourseId)}
              className="text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>

          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {documents.length === 0 ? (
              <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">
                No documents uploaded for this course yet.
              </div>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} className="py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3.5">
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                      {getDocIcon(doc.file_type)}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-900 dark:text-white">{doc.filename}</h4>
                      <div className="flex items-center gap-3 text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                        <span className="uppercase font-semibold">{doc.file_type}</span>
                        <span>•</span>
                        <span>{(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
                        <span>•</span>
                        <span className="capitalize">{doc.source_category.replace('_', ' ')}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {doc.status === 'completed' ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Indexed (100%)
                      </span>
                    ) : doc.status === 'failed' ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
                        <AlertCircle className="w-3.5 h-3.5" /> Failed
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> {doc.status} ({doc.progress}%)
                      </span>
                    )}

                    <button
                      onClick={() => handleTrashDocument(doc.id, doc.filename)}
                      title="Trash document"
                      className="p-1.5 text-slate-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      )}
    </div>
  );
};
