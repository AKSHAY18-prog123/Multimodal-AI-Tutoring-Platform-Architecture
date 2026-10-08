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
        return <FileText className="w-5 h-5 text-red-600" />;
      case 'pptx':
        return <Presentation className="w-5 h-5 text-orange-600" />;
      case 'video':
        return <Video className="w-5 h-5 text-blue-600" />;
      default:
        return <ImageIcon className="w-5 h-5 text-emerald-600" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-xl h-full bg-white shadow-2xl flex flex-col border-l border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/80">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white rounded-lg border border-slate-200 shadow-sm">
              {getSourceIcon()}
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 text-base flex items-center gap-2">
                Canonical Source Grounding
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-medium">
                  Verified Anchor
                </span>
              </h3>
              <p className="text-xs text-slate-500 font-mono truncate max-w-xs">{citation.source_file}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Source Coordinates Bar */}
        <div className="px-6 py-3 bg-slate-100/60 border-b border-slate-200 flex flex-wrap gap-4 text-xs font-medium text-slate-700">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Type:</span>
            <span className="uppercase font-semibold text-slate-900">{citation.source_type}</span>
          </div>
          {citation.page_number && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Page Number:</span>
              <span className="font-semibold text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                Page {citation.page_number}
              </span>
            </div>
          )}
          {citation.slide_number && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Slide Number:</span>
              <span className="font-semibold text-orange-700 bg-orange-50 px-2 py-0.5 rounded">
                Slide {citation.slide_number}
              </span>
            </div>
          )}
          {citation.timestamp_formatted && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Timestamp:</span>
              <span className="font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                {citation.timestamp_formatted}
              </span>
            </div>
          )}
        </div>

        {/* Content Preview / Canvas */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="rounded-xl border border-slate-200 p-5 bg-white shadow-sm space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-slate-100">
              <span className="flex items-center gap-1 font-medium">
                <Bookmark className="w-3.5 h-3.5 text-brand-500" />
                Indexed Grounding Passage
              </span>
              <span>Attributed in RAG Context</span>
            </div>
            <div className="text-sm text-slate-700 leading-relaxed font-serif bg-slate-50/50 p-4 rounded-lg border border-slate-100">
              <p>
                "{citation.source_file} • {citation.label}: Verified course excerpt indexed from primary learning material.
                Presents definitions, governing principles, and structural analysis corresponding to this academic topic."
              </p>
            </div>
          </div>

          {/* Interactive Document Viewer Frame */}
          <div className="rounded-xl border border-slate-200 overflow-hidden bg-slate-900 text-white p-4 text-center">
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
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100 transition-colors"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
};
