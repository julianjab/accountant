import React from 'react';

const AVATARS = [['#EFFDF5', '#00784A'], ['#F1EBFA', '#6A45A8'], ['#EAF1FB', '#2C5FA8'], ['#F4F1E6', '#8A7A2E'], ['#FDEEEC', '#B03A2B'], ['#ECF3F0', '#3E4A43']];

export function ClientGroupHeader({ client, count, avatarIndex = 0, onClick }) {
  const [bg, fg] = AVATARS[avatarIndex % AVATARS.length];
  const initials = client.split(' ').filter(w => w.length > 2).slice(0, 2).map(w => w[0]).join('').toUpperCase();
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px var(--gutter-card)', background: 'var(--surface-sunken)', borderBottom: '1px solid var(--border-subtle)' }}>
      <span style={{ width: 22, height: 22, flex: 'none', borderRadius: 'var(--radius-sm)', background: bg, color: fg, font: '600 10px/22px var(--font-sans)', textAlign: 'center' }}>{initials}</span>
      <button type="button" onClick={onClick} style={{ border: 0, background: 'transparent', padding: 0, fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600, color: 'var(--text-1)', cursor: 'pointer' }}>{client}</button>
      <div style={{ flex: 1 }} />
      <div style={{ font: 'var(--mono-micro)', color: 'var(--text-muted)' }}>{count}</div>
    </div>
  );
}
