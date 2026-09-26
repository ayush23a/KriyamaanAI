'use client';

import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { cn } from '../../lib/utils';

interface MarkdownContentProps {
  content: string;
  onCitationClick?: (citationId: string) => void;
  className?: string;
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({
  content,
  onCitationClick,
  className,
}) => {
  // Parse content into blocks and inline elements
  const renderBlocks = (text: string) => {
    // Split by code blocks ```lang ... ```
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    const elements: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = codeBlockRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        const textChunk = text.substring(lastIndex, match.index);
        elements.push(renderTextAndTables(textChunk, `txt-${lastIndex}`));
      }

      const lang = match[1] || 'text';
      const code = match[2].trimEnd();
      elements.push(<CodeBlock key={`code-${match.index}`} language={lang} code={code} />);

      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      elements.push(renderTextAndTables(text.substring(lastIndex), `txt-${lastIndex}`));
    }

    return elements;
  };

  const renderTextAndTables = (chunk: string, keyPrefix: string) => {
    // Check if chunk contains markdown tables
    const paragraphs = chunk.split(/\n\n+/);

    return (
      <div key={keyPrefix} className="space-y-3.5">
        {paragraphs.map((para, idx) => {
          const trimmed = para.trim();
          if (!trimmed) return null;

          // Check for table pattern
          if (trimmed.includes('|') && trimmed.includes('\n|---')) {
            return renderTable(trimmed, `${keyPrefix}-tbl-${idx}`);
          }

          // Check for blockquote
          if (trimmed.startsWith('> ')) {
            const quoteContent = trimmed.replace(/^> \s*/gm, '');
            return (
              <blockquote
                key={`${keyPrefix}-bq-${idx}`}
                className="border-l-2 border-[#C25E43] pl-4 py-1 italic text-stone-700 bg-[#FDF6F3]/50 rounded-r text-sm"
              >
                {renderInline(quoteContent)}
              </blockquote>
            );
          }

          // Check for bullet list
          if (/^[-*•]\s+/m.test(trimmed)) {
            const items = trimmed.split(/\n(?=[-•*]\s+)/);
            return (
              <ul key={`${keyPrefix}-ul-${idx}`} className="list-disc list-outside pl-5 space-y-1.5 text-stone-800 text-[15px] leading-relaxed">
                {items.map((item, itemIdx) => (
                  <li key={itemIdx}>
                    {renderInline(item.replace(/^[-•*]\s+/, ''))}
                  </li>
                ))}
              </ul>
            );
          }

          // Check for ordered list
          if (/^\d+\.\s+/m.test(trimmed)) {
            const items = trimmed.split(/\n(?=\d+\.\s+)/);
            return (
              <ol key={`${keyPrefix}-ol-${idx}`} className="list-decimal list-outside pl-5 space-y-1.5 text-stone-800 text-[15px] leading-relaxed">
                {items.map((item, itemIdx) => (
                  <li key={itemIdx}>
                    {renderInline(item.replace(/^\d+\.\s+/, ''))}
                  </li>
                ))}
              </ol>
            );
          }

          // Check for headers
          if (trimmed.startsWith('# ')) {
            return (
              <h1 key={`${keyPrefix}-h1-${idx}`} className="text-xl font-semibold text-stone-900 tracking-tight pt-2">
                {renderInline(trimmed.substring(2))}
              </h1>
            );
          }
          if (trimmed.startsWith('## ')) {
            return (
              <h2 key={`${keyPrefix}-h2-${idx}`} className="text-lg font-semibold text-stone-900 tracking-tight pt-1.5">
                {renderInline(trimmed.substring(3))}
              </h2>
            );
          }
          if (trimmed.startsWith('### ')) {
            return (
              <h3 key={`${keyPrefix}-h3-${idx}`} className="text-base font-semibold text-stone-900 pt-1">
                {renderInline(trimmed.substring(4))}
              </h3>
            );
          }

          return (
            <p key={`${keyPrefix}-p-${idx}`} className="text-stone-800 text-[15px] leading-relaxed whitespace-pre-wrap">
              {renderInline(trimmed)}
            </p>
          );
        })}
      </div>
    );
  };

  const renderTable = (tableText: string, key: string) => {
    const lines = tableText.split('\n').filter((l) => l.trim().length > 0);
    if (lines.length < 2) return null;

    const headers = lines[0]
      .split('|')
      .slice(1, -1)
      .map((h) => h.trim());

    const rows = lines.slice(2).map((rowLine) =>
      rowLine
        .split('|')
        .slice(1, -1)
        .map((c) => c.trim())
    );

    return (
      <div key={key} className="overflow-x-auto my-3 rounded-lg border border-[#E7E2DA]">
        <table className="w-full text-left border-collapse text-sm">
          <thead>
            <tr className="bg-[#F7F4EE] border-b border-[#E7E2DA]">
              {headers.map((h, i) => (
                <th key={i} className="py-2.5 px-3.5 font-medium text-stone-800">
                  {renderInline(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E7E2DA] bg-white">
            {rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-[#FAF8F5] transition-colors">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="py-2 px-3.5 text-stone-700">
                    {renderInline(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderInline = (str: string): React.ReactNode => {
    // Process citations [1], [e_xxx], etc.
    // Process bold **text**, italics *text*, code `code`
    const parts = str.split(/(\[[\w-]+\]|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);

    return parts.map((part, i) => {
      if (!part) return null;

      // Inline code
      if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
        return (
          <code
            key={i}
            className="px-1.5 py-0.5 rounded bg-[#F2EDE4] text-stone-900 font-mono text-[13px] border border-[#E7E2DA]"
          >
            {part.slice(1, -1)}
          </code>
        );
      }

      // Bold
      if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        return <strong key={i} className="font-semibold text-stone-900">{part.slice(2, -2)}</strong>;
      }

      // Italics
      if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
        return <em key={i} className="italic text-stone-800">{part.slice(1, -1)}</em>;
      }

      // Citations e.g. [1] or [e_123]
      if (/^\[([\w-]+)\]$/.test(part)) {
        const citationId = part.slice(1, -1);
        return (
          <button
            key={i}
            type="button"
            onClick={() => onCitationClick?.(citationId)}
            className="inline-flex items-center justify-center px-1.5 py-0.2 mx-0.5 -translate-y-0.5 text-xs font-medium rounded text-[#C25E43] bg-[#FDF6F3] border border-[#F1D6CE] hover:bg-[#C25E43] hover:text-white transition-colors cursor-pointer"
            title={`View citation ${citationId}`}
          >
            {citationId}
          </button>
        );
      }

      return part;
    });
  };

  return <div className={cn('prose-stone', className)}>{renderBlocks(content)}</div>;
};

interface CodeBlockProps {
  language: string;
  code: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-3 rounded-lg border border-[#E7E2DA] bg-[#F7F4EE] overflow-hidden text-sm group">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#F2EDE4]/80 border-b border-[#E7E2DA] text-xs text-stone-600 font-mono">
        <span>{language}</span>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-200/60 transition-colors"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-[#5F7143]" />
              <span className="text-[#5F7143]">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="p-3.5 overflow-x-auto">
        <pre className="text-stone-800">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
};

