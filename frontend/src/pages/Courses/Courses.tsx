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
  RefreshCw
} from 'lucide-react';
import { api } from '../../services/api';
import { DocumentItem, Course } from '../../types';

interface CoursesProps {
  onOpenAddCourse?: () => void;
}

export const Courses: React.FC<CoursesProps> = ({ onOpenAddCourse }) => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [sourceCategory, setSourceCategory] = useState<'course_source' | 'student_provided'>('course_source');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [uploadingFiles, setUploadingFiles] = useState<string[]>([]);

  useEffect(() => {
    loadCourses();
  }, []);

  useEffect(() => {
    if (selectedCourseId) {
      loadDocuments(selectedCourseId);
    } else {
      setDocuments([]);
    }
  }, [selectedCourseId]);

  // Polling for async background ingestion progress (Section 25)
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

  async function loadCourses() {
    try {
      const data = await api.listCourses();
      setCourses(data);
      if (data.length > 0 && !selectedCourseId) {
        setSelectedCourseId(data[0].id);
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
      // refresh documents list right away
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
      case 'pdf': return <FileText className="w-5 h-5 text-red-600" />;
      case 'pptx': case 'ppt': return <Presentation className="w-5 h-5 text-orange-600" />;
      case 'video': case 'mp4': return <Video className="w-5 h-5 text-blue-600" />;
      default: return <ImageIcon className="w-5 h-5 text-emerald-600" />;
    }
  };

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Course Knowledge Library</h1>
          <p className="text-sm text-slate-500 mt-1">
            Multimodal document ingestion, automated page/slide/timestamp indexing, and source provenance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {courses.length > 0 && (
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              className="px-3.5 py-2 text-sm font-semibold rounded-lg bg-white border border-slate-300 text-slate-800 shadow-2xs"
            >
              {courses.map(c => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
          )}
          <button
            onClick={onOpenAddCourse}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-semibold rounded-lg bg-brand-600 hover:bg-brand-700 text-white shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            + Add Course
          </button>
        </div>
      </div>

      {courses.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center">
            <FolderOpen className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900">Your Knowledge Library is Empty</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Add your first course and upload course materials (PDF, PPTX, Video, Images) to start multimodal indexing.
            </p>
          </div>
          <button
            onClick={onOpenAddCourse}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 text-white font-bold text-sm shadow-sm hover:bg-brand-700 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            + Add Course / Resource
          </button>
        </div>
      ) : (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Multimodal Upload Zone */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-6">
          <h2 className="font-bold text-slate-900 text-base flex items-center gap-2">
            <Upload className="w-5 h-5 text-brand-600" />
            Upload Course Materials
          </h2>

          {/* Source Category Selector */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-600 uppercase tracking-wide">Source Provenance</label>
            <div className="grid grid-cols-2 gap-2 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setSourceCategory('course_source')}
                className={`py-2 px-3 rounded-lg border transition-all ${
                  sourceCategory === 'course_source'
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                Official Course Source
              </button>
              <button
                type="button"
                onClick={() => setSourceCategory('student_provided')}
                className={`py-2 px-3 rounded-lg border transition-all ${
                  sourceCategory === 'student_provided'
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                Student Personal Note
              </button>
            </div>
          </div>

          {/* Dropzone */}
          <div className="border-2 border-dashed border-slate-300 hover:border-brand-500 rounded-xl p-6 text-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-brand-50/20 relative">
            <input
              type="file"
              multiple
              onChange={handleFileUpload}
              disabled={uploading}
              className="absolute inset-0 opacity-0 cursor-pointer"
              accept=".pdf,.pptx,.ppt,.mp4,.webm,.png,.jpg,.jpeg,.mp3,.wav"
            />
            <div className="flex flex-col items-center space-y-2">
              <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">
                <Upload className="w-5 h-5" />
              </div>
              <p className="text-sm font-semibold text-slate-800">
                {uploading
                  ? `Processing ${uploadingFiles.length} file(s)...`
                  : 'Click or drag files to upload (Multiple files supported)'}
              </p>
              <p className="text-xs text-slate-400">
                Select multiple PDF textbooks, PPTX slides, MP4 lecture videos, diagrams, or notes at once
              </p>
              {uploadingFiles.length > 0 && (
                <div className="flex flex-wrap gap-1.5 justify-center pt-2 max-w-sm">
                  {uploadingFiles.map((fn, idx) => (
                    <span key={idx} className="text-[10px] px-2 py-0.5 rounded bg-brand-100 text-brand-800 font-mono truncate max-w-[180px]">
                      📄 {fn}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Live Background Progress Bar (Section 25) */}
          {uploading && (
            <div className="rounded-xl border border-brand-200 bg-brand-50/50 p-4 space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-brand-900">
                <span className="capitalize flex items-center gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Stage: {uploadStatus?.replace('_', ' ')}
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-brand-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-brand-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-[11px] text-brand-700">
                Non-blocking async job pipeline active: vision extraction, chunking, and embedding.
              </p>
            </div>
          )}
        </div>

        {/* Right Column: Ingested Document Inventory */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-brand-600" />
              Indexed Documents & Sources ({documents.length})
            </h2>
            <button
              onClick={() => selectedCourseId && loadDocuments(selectedCourseId)}
              className="text-xs font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {documents.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-sm">
                No documents uploaded for this course yet.
              </div>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} className="py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3.5">
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                      {getDocIcon(doc.file_type)}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">{doc.filename}</h4>
                      <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
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
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Indexed (100%)
                      </span>
                    ) : doc.status === 'failed' ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700">
                        <AlertCircle className="w-3.5 h-3.5" /> Failed
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> {doc.status} ({doc.progress}%)
                      </span>
                    )}
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
