import React from 'react';

export function Tag({ tone = 'neutral', mono = false, children }) {
  const tones = {
    neutral: { background: 'var(--surface-card)', color: 'var(--text-2)', border: '1px solid var(--border-default)' },
    accent: { background: 'var(--accent-soft)', color: 'var(--status-processed-fg)', border: '1px solid transparent' },
    warn: { background: 'var(--status-pending-bg)', color: 'var(--status-pending-fg)', border: '1px solid transparent' },
    onDeep: { background: 'rgba(0,220,130,.13)', color: 'var(--color-green-300)', border: '1px solid transparent' }
  };
  return (
    <span style={{ font: mono ? 'var(--mono-micro)' : '400 11.5px/1 var(--font-sans)', padding: mono ? '4px 7px' : '3px 9px', borderRadius: mono ? 'var(--radius-sm)' : 'var(--radius-pill)', ...tones[tone] }}>{children}</span>
  );
}
