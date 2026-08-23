import React from 'react';

const STATUS = {
  pending: ['Pendiente', 'var(--status-pending-bg)', 'var(--status-pending-fg)'],
  classifying: ['Clasificando', 'var(--status-classifying-bg)', 'var(--status-classifying-fg)'],
  running_ocr: ['OCR', 'var(--status-ocr-bg)', 'var(--status-ocr-fg)'],
  processed: ['Procesado', 'var(--status-processed-bg)', 'var(--status-processed-fg)'],
  failed: ['Fallido', 'var(--status-failed-bg)', 'var(--status-failed-fg)']
};

export function StatusBadge({ status = 'pending', label }) {
  const [text, bg, fg] = STATUS[status] || STATUS.pending;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, font: '500 12px/1 var(--font-sans)', padding: '3px 9px', borderRadius: 'var(--radius-pill)', background: bg, color: fg }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: fg }} />
      {label || text}
    </span>
  );
}
