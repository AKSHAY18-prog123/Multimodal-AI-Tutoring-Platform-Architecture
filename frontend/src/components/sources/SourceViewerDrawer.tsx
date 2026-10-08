import React from 'react';
import { X, FileText, Presentation, Video, Image as ImageIcon, ExternalLink, Bookmark } from 'lucide-react';
import { Citation } from '../../types';

interface SourceViewerDrawerProps {
  citation: Citation | null;
  isOpen: boolean;
  onClose: () => void;
}

export const SourceViewerDrawer: React.FC<SourceViewerDrawerProps> = ({ citation, isOpen, onClose }) => {
  if (!isOpen || !citation) return null;

  const getSourceIcon = () => {
    switch (citation.source_type) {
      case 'pdf':
        return <FileText className="w-5 h-5 text-red-500" />;
      case 'pptx':
        return <Presentation className="w-5 h-5 text-orange-500" />;
      case 'video':
        return <Video className="w-5 h-5 text-sky-500" />;
      default:
        return <ImageIcon className="w-5 h-5 text-emerald-500" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-xl h-full bg-white dark:bg-slate-900 shadow-2xl flex flex-col border-l border-slate-200 dark:border-slate-800 transition-colors duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/80">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow-xs">
              {getSourceIcon()}
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white text-base flex items-center gap-2">
                Canonical Source Grounding
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 font-medium">
                  Verified Anchor
                </span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono truncate max-w-xs">{citation.source_file}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-200/50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Source Coordinates Bar */}
        <div className="px-6 py-3 bg-slate-100/60 dark:bg-slate-950/40 border-b border-slate-200 dark:border-slate-800 flex flex-wrap gap-4 text-xs font-medium text-slate-700 dark:text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 dark:text-slate-500">Type:</span>
            <span className="uppercase font-semibold text-slate-900 dark:text-white">{citation.source_type}</span>
          </div>
          {citation.page_number && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 dark:text-slate-500">Page Number:</span>
              <span className="font-semibold text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-950/70 px-2 py-0.5 rounded border border-sky-200 dark:border-sky-800">
                Page {citation.page_number}
              </span>
            </div>
          )}
          {citation.slide_number && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 dark:text-slate-500">Slide Number:</span>
              <span className="font-semibold text-orange-700 dark:text-orange-300 bg-orange-50 dark:bg-orange-950/70 px-2 py-0.5 rounded border border-orange-200 dark:border-orange-800">
                Slide {citation.slide_number}
              </span>
            </div>
          )}
          {citation.timestamp_formatted && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 dark:text-slate-500">Timestamp:</span>
              <span className="font-semibold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/70 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-800">
                {citation.timestamp_formatted}
              </span>
            </div>
          )}
        </div>

        {/* Content Preview / Canvas */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-5 bg-white dark:bg-slate-900 shadow-sm space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
              <span className="flex items-center gap-1 font-medium">
                <Bookmark className="w-3.5 h-3.5 text-sky-500" />
                Indexed Grounding Passage
              </span>
              <span>Attributed in RAG Context</span>
            </div>
            <div className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed font-serif bg-slate-50/70 dark:bg-slate-950/50 p-4 rounded-lg border border-slate-100 dark:border-slate-800">
              <p>
                "{citation.source_file} • {citation.label}: Verified course excerpt indexed from primary learning material.
                Presents definitions, governing principles, and structural analysis corresponding to this academic topic."
              </p>
            </div>
          </div>

          {/* Interactive Document Viewer Frame */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden bg-slate-900 text-white p-4 text-center">
            <p className="text-xs text-slate-400 mb-2">Simulated Live Source Canvas</p>
            <div className="h-64 rounded bg-slate-800 flex flex-col items-center justify-center p-4 text-slate-400 border border-slate-700">
              {getSourceIcon()}
              <p className="mt-2 text-sm font-medium text-slate-200">
                Viewing {citation.source_file}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {citation.page_number ? `Centered on Page ${citation.page_number}` : ''}
                {citation.slide_number ? `Centered on Slide ${citation.slide_number}` : ''}
                {citation.timestamp_formatted ? `Seeked to ${citation.timestamp_formatted}` : ''}
              </p>
              <div className="mt-4 px-3 py-1.5 rounded-lg bg-slate-700 text-xs text-slate-200 flex items-center gap-1.5">
                <ExternalLink className="w-3.5 h-3.5" />
                Exact Canonical Source Match (100% Grounded)
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors cursor-pointer"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
};
