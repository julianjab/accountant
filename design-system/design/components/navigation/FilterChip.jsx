import React from 'react';

export function FilterChip({ label, active = false, onClick }) {
  return (
    <button type="button" onClick={onClick} style={{ border: `1px solid ${active ? 'var(--surface-deep)' : 'var(--color-line-150)'}`, background: active ? 'var(--surface-deep)' : 'var(--surface-card)', color: active ? 'var(--color-white)' : 'var(--text-2)', fontFamily: 'var(--font-sans)', fontSize: 12.5, fontWeight: 500, padding: '5px 11px', borderRadius: 'var(--radius-pill)', cursor: 'pointer' }}>{label}</button>
  );
}
