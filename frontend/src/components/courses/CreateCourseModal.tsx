import React, { useState, useEffect } from 'react';
import { 
  X, 
  BookOpen, 
  Upload, 
  CheckCircle2, 
  RefreshCw, 
  AlertCircle, 
  FileText, 
  Presentation, 
  Video, 
  ArrowRight,
  Zap,
  Network
} from 'lucide-react';
import { api } from '../../services/api';

interface CreateCourseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCourseCreated: (course: any, meta?: { startDiagnostic?: boolean }) => void;
}

export const CreateCourseModal: React.FC<CreateCourseModalProps> = ({
  isOpen,
  onClose,
  onCourseCreated
}) => {
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('');
  const [code, setCode] = useState('');
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  
  // State machine: 'form' | 'processing' | 'ready'
  const [phase, setPhase] = useState<'form' | 'processing' | 'ready'>('form');
  const [createdCourse, setCreatedCourse] = useState<any | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('uploaded');
  const [error, setError] = useState<string | null>(null);

  // Background polling during document ingestion
  useEffect(() => {
    if (!activeJobId || phase !== 'processing') return;

    const interval = setInterval(async () => {
      try {
        const res = await api.getDocumentStatus(activeJobId);
        setProgress(res.progress);
        setStage(res.status);

        if (res.status === 'completed') {
          clearInterval(interval);
          setPhase('ready');
        } else if (res.status === 'failed') {
          clearInterval(interval);
          setError(res.error_message || 'Document processing failed.');
        }
      } catch (err: any) {
        console.error("Polling error:", err);
      }
    }, 1200);

    return () => clearInterval(interval);
  }, [activeJobId, phase]);

  if (!isOpen) return null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setError(null);
    try {
      const course = await api.createCourse({
        title: title.trim(),
        subject: subject.trim() || undefined,
        code: code.trim() || undefined,
        description: description.trim() || undefined
      });
      setCreatedCourse(course);

      if (files.length > 0) {
        setPhase('processing');
        setProgress(15);
        setStage('extracting');
        const uploadRes = await api.uploadDocumentsBatch(course.id, files, 'course_source');
        if (uploadRes.job_ids && uploadRes.job_ids.length > 0) {
          setActiveJobId(uploadRes.job_ids[uploadRes.job_ids.length - 1]);
        }
      } else {
        // No file uploaded, course created directly
        onCourseCreated(course);
        onClose();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create course.');
    }
  };

  const getStageLabel = (st: string) => {
    switch (st) {
      case 'extracting': return '1/5 Extracting text, headings & equations';
      case 'transcribing': return '2/5 Transcribing lecture audio timestamps';
      case 'vision_analysis': return '2/5 Analyzing diagrams with Multimodal Vision';
      case 'chunking': return '3/5 Semantic chunking with page/slide provenance';
      case 'indexing': return '4/5 Generating embeddings & indexing vector store';
      case 'knowledge_graph': return '5/5 Constructing topic hierarchy & prerequisite DAG';
      case 'completed': return 'Completed! Ready for learning';
      default: return `Processing (${st})`;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-md p-4 animate-fade-in">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-brand-100 text-brand-700 rounded-xl">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">
                {phase === 'ready' ? 'Course Setup Complete!' : 'Add New Course / Learning Material'}
              </h3>
              <p className="text-xs text-slate-500">
                Works with any academic subject, textbook, slide deck, or lecture.
              </p>
            </div>
          </div>
          {phase !== 'processing' && (
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Phase 1: Course Info Form */}
        {phase === 'form' && (
          <form onSubmit={handleCreate} className="p-6 space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Course Title *
              </label>
              <input
                type="text"
                required
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Computer Networks, Organic Chemistry, Deep Learning"
                className="w-full px-4 py-2.5 text-sm bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 font-medium text-slate-900"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Subject / Discipline
                </label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g., Computer Science, Biology"
                  className="w-full px-3.5 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Course Code <span className="text-slate-400 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="e.g., CS 455, CHEM 201"
                  className="w-full px-3.5 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                />
              </div>
            </div>

            {/* Document Upload Zone */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Upload Course Materials <span className="text-slate-400 font-normal">(Multiple PDFs, PPTXs, Videos, Images)</span>
              </label>
              <div className="border-2 border-dashed border-slate-300 hover:border-brand-500 rounded-xl p-4 text-center cursor-pointer bg-slate-50 hover:bg-brand-50/20 relative transition-colors">
                <input
                  type="file"
                  multiple
                  onChange={(e) => setFiles(Array.from(e.target.files || []))}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  accept=".pdf,.pptx,.ppt,.mp4,.webm,.png,.jpg,.jpeg,.mp3,.wav"
                />
                <div className="flex flex-col items-center space-y-1">
                  <Upload className="w-5 h-5 text-slate-400" />
                  <p className="text-xs font-semibold text-slate-700">
                    {files.length > 0
                      ? `${files.length} file(s) selected: ${files.map(f => f.name).join(', ')}`
                      : 'Choose course PDFs, lecture slides, or lecture videos (multiple files supported)'}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    Extracts text, slides, diagrams, and builds knowledge graph automatically
                  </p>
                </div>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
                {error}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!title.trim()}
                className="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm shadow-sm transition-all"
              >
                {files.length > 0 ? `Create & Ingest (${files.length}) Materials →` : 'Create Course'}
              </button>
            </div>
          </form>
        )}

        {/* Phase 2: Asynchronous Real-Time Pipeline Processing */}
        {phase === 'processing' && (
          <div className="p-8 space-y-6 text-center">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center animate-pulse shadow-sm">
              <RefreshCw className="w-8 h-8 animate-spin" />
            </div>

            <div className="space-y-1.5">
              <h4 className="text-base font-bold text-slate-900">
                Processing {files.length > 1 ? `${files.length} learning resources` : `"${files[0]?.name || 'material'}"`}
              </h4>
              <p className="text-xs font-medium text-brand-700">
                {getStageLabel(stage)}
              </p>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-semibold text-slate-500">
                <span>Pipeline Progress</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-brand-600 h-2.5 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Pipeline Stage Indicators */}
            <div className="grid grid-cols-5 gap-1.5 text-[10px] text-slate-400 font-medium">
              <span className={progress >= 20 ? 'text-brand-700 font-bold' : ''}>Extract</span>
              <span className={progress >= 45 ? 'text-brand-700 font-bold' : ''}>Vision</span>
              <span className={progress >= 65 ? 'text-brand-700 font-bold' : ''}>Chunk</span>
              <span className={progress >= 85 ? 'text-brand-700 font-bold' : ''}>Index</span>
              <span className={progress >= 95 ? 'text-brand-700 font-bold' : ''}>Graph</span>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
                {error}
              </div>
            )}
          </div>
        )}

        {/* Phase 3: Ingestion Complete — Option to Calibrate or Learn */}
        {phase === 'ready' && (
          <div className="p-8 space-y-6 text-center">
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shadow-sm">
              <CheckCircle2 className="w-9 h-9" />
            </div>

            <div className="space-y-1.5">
              <h4 className="text-lg font-bold text-slate-900">
                "{createdCourse?.title}" is Ready!
              </h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Multimodal knowledge base, vector embeddings, and concept prerequisite DAG have been successfully constructed.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-3 text-left pt-2">
              <button
                onClick={() => {
                  onCourseCreated(createdCourse, { startDiagnostic: true });
                  onClose();
                }}
                className="p-4 rounded-2xl border-2 border-brand-500 bg-brand-50/40 hover:bg-brand-50 hover:shadow-md transition-all group"
              >
                <div className="flex items-center justify-between font-bold text-xs text-brand-900 mb-1">
                  <span className="flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-brand-600" />
                    Option A: Take 3-Min Diagnostic
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
                <p className="text-[11px] text-slate-600">
                  Quickly assess your starting knowledge level for this material.
                </p>
              </button>

              <button
                onClick={() => {
                  onCourseCreated(createdCourse, { startDiagnostic: false });
                  onClose();
                }}
                className="p-4 rounded-2xl border border-slate-200 bg-white hover:border-brand-400 hover:shadow-md transition-all group"
              >
                <div className="flex items-center justify-between font-bold text-xs text-slate-800 mb-1">
                  <span className="flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-slate-600" />
                    Option B: Start Tutoring
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
                <p className="text-[11px] text-slate-500">
                  Jump right into questions and interactive chat grounded in your materials.
                </p>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
