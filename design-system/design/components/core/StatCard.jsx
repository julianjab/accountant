import React from 'react';

export function StatCard({ label, value, note, tone = 'default' }) {
  const color = { default: 'var(--text-1)', accent: 'var(--accent)', danger: 'var(--status-failed-fg)' }[tone];
  return (
    <div style={{ background: 'var(--surface-card)', border: 'var(--border-hairline)', borderRadius: 'var(--radius-lg)', padding: '15px 16px' }}>
      <div style={{ font: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-muted)' }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 8 }}>
        <div style={{ font: 'var(--mono-figure)', letterSpacing: '-0.03em', color }}>{value}</div>
        {note && <div style={{ font: 'var(--text-meta)', color: 'var(--text-muted)' }}>{note}</div>}
      </div>
    </div>
  );
}
