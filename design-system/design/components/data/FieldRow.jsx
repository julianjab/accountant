import React from 'react';

export function FieldRow({ fieldKey, value, confidence }) {
  const low = typeof confidence === 'number' && confidence <= 0.9;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '170px 1fr 62px', alignItems: 'center', gap: 10, padding: '10px var(--gutter-card)', borderBottom: 'var(--border-row-line)' }}>
      <div style={{ font: 'var(--mono-micro)', color: 'var(--text-muted)' }}>{fieldKey}</div>
      <div style={{ font: 'var(--text-body-strong)', color: low ? 'var(--status-pending-fg)' : 'var(--text-1)' }}>{value}</div>
      {typeof confidence === 'number' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, justifySelf: 'end' }}>
          <div style={{ width: 34, height: 4, borderRadius: 3, background: 'var(--border-subtle)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: Math.round(confidence * 100) + '%', background: low ? '#D9A420' : 'var(--accent-hover)' }} />
          </div>
          <span style={{ font: 'var(--mono-micro)', color: 'var(--text-muted)' }}>{confidence.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
}
