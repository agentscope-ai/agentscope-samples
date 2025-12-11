import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function MarkdownModal({ isOpen, onClose, content, agentName, reportType = 'analysis' }) {
  if (!isOpen) return null;

  const subtitle = reportType === 'decision' ? 'Decision Log' : 'Financial Analysis Report';

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(4px)',
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '2px',
          padding: '0',
          maxWidth: '900px',
          maxHeight: '85vh',
          overflow: 'hidden',
          width: '90%',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
          border: '1px solid #e0e0e0',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '24px 32px',
          borderBottom: '2px solid #000',
          backgroundColor: '#fafafa',
        }}>
          <div>
            <h2 style={{
              margin: 0,
              fontSize: '18px',
              fontWeight: 700,
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
              color: '#000',
            }}>
              {agentName}
            </h2>
            <p style={{
              margin: '4px 0 0 0',
              fontSize: '12px',
              color: '#666',
              fontWeight: 500,
              letterSpacing: '0.3px',
            }}>
              {subtitle}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#000',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#fff',
              width: '32px',
              height: '32px',
              borderRadius: '2px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              outline: 'none',
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#333'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#000'}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{
          padding: '32px 32px 24px 32px',
          overflow: 'auto',
          backgroundColor: '#fff',
          flex: 1,
        }}>
          <style>{`
            .markdown-content {
              color: #1a1a1a;
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            }

            .markdown-content h1 {
              font-size: 24px;
              font-weight: 700;
              margin: 32px 0 16px 0;
              padding-bottom: 12px;
              border-bottom: 2px solid #000;
              color: #000;
              letter-spacing: 0.3px;
              text-transform: uppercase;
            }

            .markdown-content h1:first-child {
              margin-top: 0;
            }

            .markdown-content h2 {
              font-size: 20px;
              font-weight: 700;
              margin: 28px 0 12px 0;
              color: #000;
              letter-spacing: 0.3px;
              text-transform: uppercase;
              padding-bottom: 8px;
              border-bottom: 1px solid #d0d0d0;
            }

            .markdown-content h3 {
              font-size: 16px;
              font-weight: 700;
              margin: 24px 0 10px 0;
              color: #1a1a1a;
              letter-spacing: 0.2px;
            }

            .markdown-content h4 {
              font-size: 14px;
              font-weight: 700;
              margin: 20px 0 8px 0;
              color: #2a2a2a;
              text-transform: uppercase;
              letter-spacing: 0.5px;
            }

            .markdown-content p {
              margin: 12px 0;
              line-height: 1.8;
              font-size: 14px;
              color: #2a2a2a;
            }

            .markdown-content table {
              border-collapse: collapse;
              width: 100%;
              margin: 24px 0;
              font-size: 13px;
              border: 1px solid #000;
              background: #fff;
            }

            .markdown-content th {
              background-color: #000;
              color: #fff;
              padding: 12px 16px;
              text-align: left;
              font-weight: 700;
              letter-spacing: 0.5px;
              text-transform: uppercase;
              font-size: 12px;
              border: 1px solid #000;
            }

            .markdown-content td {
              border: 1px solid #d0d0d0;
              padding: 12px 16px;
              text-align: left;
              color: #1a1a1a;
            }

            .markdown-content tr:nth-child(even) {
              background-color: #fafafa;
            }

            .markdown-content tr:hover {
              background-color: #f0f0f0;
            }

            .markdown-content ul,
            .markdown-content ol {
              margin: 16px 0;
              padding-left: 28px;
              line-height: 1.8;
            }

            .markdown-content li {
              margin: 8px 0;
              color: #2a2a2a;
              font-size: 14px;
            }

            .markdown-content li::marker {
              color: #000;
              font-weight: 700;
            }

            .markdown-content strong {
              font-weight: 700;
              color: #000;
            }

            .markdown-content em {
              font-style: italic;
              color: #3a3a3a;
            }

            .markdown-content code {
              background-color: #f5f5f5;
              padding: 3px 8px;
              border-radius: 2px;
              font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
              font-size: 13px;
              color: #000;
              border: 1px solid #e0e0e0;
            }

            .markdown-content pre {
              background-color: #fafafa;
              padding: 16px;
              border-radius: 2px;
              overflow-x: auto;
              margin: 20px 0;
              border: 1px solid #d0d0d0;
              border-left: 3px solid #000;
            }

            .markdown-content pre code {
              background: none;
              padding: 0;
              border: none;
              font-size: 13px;
            }

            .markdown-content blockquote {
              border-left: 4px solid #000;
              margin: 20px 0;
              padding: 12px 20px;
              background-color: #fafafa;
              color: #2a2a2a;
              font-style: italic;
            }

            .markdown-content hr {
              border: none;
              border-top: 1px solid #d0d0d0;
              margin: 32px 0;
            }
          `}</style>
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MarkdownModal;

