import React from 'react';

export function Card({ tone = 'light', padded = true, title, action, children }) {
  const deep = tone === 'deep';
  return (
    <div style={{ background: deep ? 'var(--surface-deep)' : 'var(--surface-card)', border: deep ? 'none' : 'var(--border-hairline)', borderRadius: 'var(--radius-xl)', overflow: 'hidden', color: deep ? 'var(--text-on-deep)' : 'var(--text-1)' }}>
      {title && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '13px var(--gutter-card)', borderBottom: deep ? '1px solid rgba(255,255,255,.09)' : '1px solid var(--border-subtle)' }}>
          <div style={{ font: 'var(--text-body-strong)', fontWeight: 600 }}>{title}</div>
          <div style={{ flex: 1 }} />
          {action}
        </div>
      )}
      <div style={{ padding: padded ? 'var(--gutter-card)' : 0 }}>{children}</div>
    </div>
  );
}
