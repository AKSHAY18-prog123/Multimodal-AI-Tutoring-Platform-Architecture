import React from 'react';
import katex from 'katex';
import { Citation } from '../../types';
import { FileText, ArrowRight, Table, Layers, Code } from 'lucide-react';
import { MermaidDiagram } from './MermaidDiagram';

interface FormattedMessageProps {
  content: string;
  citations?: Citation[];
  onCitationClick?: (citation: Citation) => void;
  isUser?: boolean;
}

const CodeBlock: React.FC<{ code: string; lang?: string }> = ({ code, lang }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-slate-700/80 bg-slate-950 shadow-md">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900 border-b border-slate-800 text-xs">
        <span className="font-mono text-[11px] uppercase tracking-wider text-sky-400 font-semibold">
          {lang || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded text-slate-300 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-3.5 text-xs font-mono overflow-x-auto text-slate-100 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
};

export const FormattedMessage: React.FC<FormattedMessageProps> = ({
  content,
  citations = [],
  onCitationClick,
  isUser = false
}) => {
  if (isUser) {
    return <div className="whitespace-pre-wrap">{content}</div>;
  }

  // Pre-process: Clean up stray quadruple asterisks, raw br tags, and normalize formulas
  const cleanContent = content
    .replace(/\*{4,}/g, '')
    .replace(/<br\s*\/?>/gi, '\n')
    // Auto-fix missing parentheses in Normal equation: X^TX^{-1} -> (X^T X)^{-1}
    .replace(/X\^T\s*X\^\{-1\}/g, '(X^T X)^{-1}')
    .replace(/X\^TX\^\{-1\}/g, '(X^T X)^{-1}')
    .replace(/X\^T\s*X\^-1/g, '(X^T X)^{-1}')
    .replace(/X\^TX\^-1/g, '(X^T X)^{-1}')
    .trim();

  // Helper to safely render KaTeX math
  const renderMath = (math: string, displayMode: boolean = false): React.ReactNode => {
    try {
      const html = katex.renderToString(math.trim(), {
        displayMode,
        throwOnError: true,
      });
      return (
        <span
          className={displayMode ? "katex-display-wrapper inline-block my-1" : "katex-inline-wrapper mx-0.5"}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      );
    } catch {
      return <code className="font-mono text-xs px-1 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded">{math}</code>;
    }
  };

  // Helper to render inline elements (citations, math, bold, code)
  const renderInline = (text: string): React.ReactNode[] => {
    // Regex matches:
    // 1. [Source: ...] citations
    // 2. $$...$$ or \[...\] display math inline
    // 3. \(...\) or $...$ inline LaTeX math
    // 4. **bold** or __bold__
    // 5. `code`
    const regex = /(\[Source:\s*[^\]]+\])|(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\])|(\\\([^\n]+?\\\)|(?<!\\)\$[^\$\n]+?\$)|(\*\*[^*]+\*\*|__[^_]+__)|(`[^`]+`)/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }

      const fullMatch = match[0];

      // 1. Citation
      if (match[1]) {
        const label = fullMatch;
        const matchedCitation = citations.find(
          c => c.label.toLowerCase() === label.toLowerCase() ||
               label.toLowerCase().includes(c.source_file.toLowerCase())
        );

        if (onCitationClick && matchedCitation) {
          parts.push(
            <button
              key={`cite-${match.index}`}
              onClick={(e) => {
                e.stopPropagation();
                onCitationClick(matchedCitation);
              }}
              className="inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-sky-100/80 dark:bg-sky-950/70 border border-sky-300 dark:border-sky-800 text-sky-800 dark:text-sky-300 hover:bg-sky-200 dark:hover:bg-sky-900 transition-colors cursor-pointer align-baseline"
              title="Click to view exact source in material"
            >
              <FileText className="w-3 h-3 text-sky-600 dark:text-sky-400 shrink-0" />
              <span>{label.replace(/[\[\]]/g, '')}</span>
            </button>
          );
        } else {
          parts.push(
            <span
              key={`cite-text-${match.index}`}
              className="inline-flex items-center gap-1 mx-1 px-1.5 py-0.5 rounded text-[11px] font-medium bg-slate-200/70 dark:bg-slate-700/60 text-slate-700 dark:text-slate-300 border border-slate-300/50 dark:border-slate-600 align-baseline"
            >
              <FileText className="w-2.5 h-2.5 opacity-70" />
              {label.replace(/[\[\]]/g, '')}
            </span>
          );
        }
      }
      // 2. Display Math: $$...$$ or \[...\]
      else if (match[2]) {
        const raw = match[2];
        const mathExpr = raw.startsWith('$$') ? raw.slice(2, -2) : raw.slice(2, -2);
        parts.push(
          <span key={`math-d-${match.index}`}>
            {renderMath(mathExpr, true)}
          </span>
        );
      }
      // 3. Inline LaTeX math: \(...\) or $...$
      else if (match[3]) {
        const raw = match[3];
        const mathExpr = raw.startsWith('\\(') ? raw.slice(2, -2) : raw.slice(1, -1);
        parts.push(
          <span key={`math-i-${match.index}`}>
            {renderMath(mathExpr, false)}
          </span>
        );
      }
      // 4. Bold text
      else if (match[4]) {
        const rawBold = match[4];
        const innerText = rawBold.slice(2, -2).trim();
        parts.push(
          <strong key={`bold-${match.index}`} className="font-semibold text-slate-900 dark:text-white">
            {innerText}
          </strong>
        );
      }
      // 5. Code: `code`
      else if (match[5]) {
        const codeText = match[5].slice(1, -1);
        parts.push(
          <code key={`code-${match.index}`} className="px-1.5 py-0.5 rounded text-xs font-mono bg-slate-200/80 dark:bg-slate-700 text-sky-700 dark:text-sky-300">
            {codeText}
          </code>
        );
      }

      lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts;
  };

  // Split lines into structured blocks
  const lines = cleanContent.split('\n');
  const blocks: React.ReactNode[] = [];
  let currentList: { type: 'ul' | 'ol'; items: string[] } | null = null;

  const flushList = () => {
    if (!currentList) return;
    if (currentList.type === 'ul') {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="my-2.5 space-y-2 pl-1">
          {currentList.items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-slate-800 dark:text-slate-200">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-500 dark:bg-sky-400 mt-2 shrink-0" />
              <div className="flex-1 leading-relaxed">
                {renderInline(item)}
              </div>
            </li>
          ))}
        </ul>
      );
    } else {
      blocks.push(
        <ol key={`ol-${blocks.length}`} className="my-2.5 space-y-2 pl-1">
          {currentList.items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2.5 text-slate-800 dark:text-slate-200">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-300 text-xs font-semibold shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <div className="flex-1 leading-relaxed">
                {renderInline(item)}
              </div>
            </li>
          ))}
        </ol>
      );
    }
    currentList = null;
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();

    if (!line) {
      flushList();
      i++;
      continue;
    }

    // 0. Code Blocks (including ```mermaid flowcharts and generic code)
    if (line.startsWith('```')) {
      flushList();
      const lang = line.slice(3).trim().toLowerCase();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) {
        i++; // skip closing ```
      }
      const codeContent = codeLines.join('\n');

      if (lang === 'mermaid') {
        blocks.push(
          <MermaidDiagram key={`mermaid-${i}`} chart={codeContent} />
        );
      } else {
        blocks.push(
          <CodeBlock key={`codeblock-${i}`} code={codeContent} lang={lang} />
        );
      }
      continue;
    }

    // 1. Multi-line or Standalone Math Block ($$ ... $$ or \[ ... \])
    if (line.startsWith('$$') || line.startsWith('\\[')) {
      flushList();
      const isBracket = line.startsWith('\\[');
      const endMarker = isBracket ? '\\]' : '$$';
      let mathContent = '';
      if (line.endsWith(endMarker) && line.length > 2) {
        mathContent = line.slice(2, -2).trim();
        i++;
      } else {
        const mathLines: string[] = [line.slice(2)];
        i++;
        while (i < lines.length && !lines[i].trim().endsWith(endMarker)) {
          if (lines[i].trim().startsWith('#') || lines[i].trim().startsWith('```')) {
            break; // Stop if we hit a heading or code block - don't swallow the rest of the text
          }
          mathLines.push(lines[i]);
          i++;
        }
        if (i < lines.length && lines[i].trim().endsWith(endMarker)) {
          const lastLine = lines[i].trim();
          mathLines.push(lastLine.slice(0, -2));
          i++;
        }
        mathContent = mathLines.join('\n').trim();
      }

      if (mathContent) {
        blocks.push(
          <div
            key={`mathblock-${i}`}
            className="my-3 py-3 px-4 overflow-x-auto rounded-xl bg-slate-50 dark:bg-slate-900/90 border border-slate-200/80 dark:border-slate-800 text-center shadow-xs"
          >
            {renderMath(mathContent, true)}
          </div>
        );
      }
      continue;
    }

    // 2. Markdown Table Detection (| col1 | col2 | ...)
    if (line.startsWith('|') && line.endsWith('|')) {
      flushList();
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        const parseRow = (rowStr: string) =>
          rowStr.slice(1, -1).split('|').map(c => c.trim());

        const headerRow = parseRow(tableLines[0]);
        const dataRows = tableLines
          .slice(1)
          .filter(r => !/^\|[\s\-:]+(\|[\s\-:]+)+\|$/.test(r)) // skip separator
          .map(parseRow);

        blocks.push(
          <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
            <table className="min-w-full text-xs text-center border-collapse">
              <thead>
                <tr className="bg-slate-100 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
                  {headerRow.map((cell, cIdx) => (
                    <th key={cIdx} className="px-3 py-2 font-semibold text-slate-800 dark:text-slate-200">
                      {renderInline(cell)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                {dataRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3 py-2 text-slate-700 dark:text-slate-300">
                        {renderInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // 3. Flow / Pipeline Architecture Diagram Detection (Any Subject: OS, Networks, Compilers, DL, DB, etc.)
    const cleanFlowCandidate = line.replace(/^`+|`+$/g, '').trim();
    const isFlowLine =
      (cleanFlowCandidate.includes('→') || cleanFlowCandidate.includes('->') || cleanFlowCandidate.includes('-->') || cleanFlowCandidate.includes('=>')) &&
      !cleanFlowCandidate.startsWith('#') &&
      cleanFlowCandidate.split(/(?:\s*→\s*|\s*->\s*|\s*-->\s*|\s*=>\s*)/).length >= 2;

    if (isFlowLine) {
      flushList();
      const rawSteps = cleanFlowCandidate.split(/(?:\s*→\s*|\s*->\s*|\s*-->\s*|\s*=>\s*)/).filter(s => s.trim().length > 0);

      blocks.push(
        <div
          key={`flow-${i}`}
          className="my-3 p-3.5 rounded-xl bg-gradient-to-r from-sky-500/5 via-indigo-500/5 to-cyan-500/5 dark:from-sky-950/40 dark:via-indigo-950/40 dark:to-cyan-950/40 border border-sky-200/70 dark:border-sky-800/70 shadow-xs"
        >
          <div className="flex items-center gap-1.5 mb-2.5 text-[11px] font-bold uppercase tracking-wider text-sky-700 dark:text-sky-300">
            <Layers className="w-3.5 h-3.5 text-sky-500" />
            <span>Architecture / Sequence Flow</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {rawSteps.map((step, sIdx) => (
              <React.Fragment key={sIdx}>
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-xs text-xs font-semibold text-slate-900 dark:text-slate-100">
                  <span className="w-4 h-4 rounded-full bg-sky-100 dark:bg-sky-900/80 text-sky-700 dark:text-sky-300 text-[10px] flex items-center justify-center font-bold shrink-0">
                    {sIdx + 1}
                  </span>
                  <span>{renderInline(step.trim())}</span>
                </div>
                {sIdx < rawSteps.length - 1 && (
                  <ArrowRight className="w-3.5 h-3.5 text-sky-500 dark:text-sky-400 shrink-0" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      );
      i++;
      continue;
    }

    // 4. Headers (### Heading, ## Heading, # Heading)
    const headerMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headerMatch) {
      flushList();
      const level = headerMatch[1].length;
      const text = headerMatch[2];
      const headerClasses = level === 1
        ? "text-base font-bold text-slate-900 dark:text-white mt-4 mb-2 border-b border-slate-200 dark:border-slate-700 pb-1"
        : level === 2
        ? "text-sm font-bold text-slate-900 dark:text-white mt-3.5 mb-1.5"
        : "text-xs font-bold text-sky-600 dark:text-sky-400 uppercase tracking-wider mt-3 mb-1";
      blocks.push(
        <div key={`h-${i}`} className={headerClasses}>
          {renderInline(text)}
        </div>
      );
      i++;
      continue;
    }

    // 5. Bullet list item: * text, - text, • text
    const bulletMatch = line.match(/^[\*\-•]\s+(.+)$/);
    if (bulletMatch) {
      if (!currentList || currentList.type !== 'ul') {
        flushList();
        currentList = { type: 'ul', items: [] };
      }
      currentList.items.push(bulletMatch[1]);
      i++;
      continue;
    }

    // 6. Numbered list item: 1. text, 2) text
    const numMatch = line.match(/^\d+[\.\)]\s+(.+)$/);
    if (numMatch) {
      if (!currentList || currentList.type !== 'ol') {
        flushList();
        currentList = { type: 'ol', items: [] };
      }
      currentList.items.push(numMatch[1]);
      i++;
      continue;
    }

    // 7. Regular paragraph
    flushList();

    // Check if line is a standalone bold title like **Core Concepts**
    const standaloneBoldMatch = line.match(/^\*\*([^*]+)\*\*:?$/);
    if (standaloneBoldMatch) {
      blocks.push(
        <div key={`title-${i}`} className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider mt-3 mb-1 text-sky-600 dark:text-sky-400">
          {standaloneBoldMatch[1]}
        </div>
      );
      i++;
      continue;
    }

    blocks.push(
      <p key={`p-${i}`} className="leading-relaxed text-slate-800 dark:text-slate-200 my-1.5">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  flushList();

  return (
    <div className="space-y-1.5 text-sm text-slate-800 dark:text-slate-100">
      {blocks}
    </div>
  );
};
