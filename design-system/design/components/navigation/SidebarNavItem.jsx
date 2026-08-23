import React from 'react';

export function SidebarNavItem({ icon, label, count, active = false, onClick }) {
  return (
    <button type="button" onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%', textAlign: 'left', border: 0, cursor: 'pointer', padding: '9px 10px', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-sans)', fontSize: 13.5, fontWeight: 500, background: active ? 'rgba(0,220,130,.12)' : 'transparent', color: active ? 'var(--accent-on-deep)' : 'rgba(230,237,233,.72)' }}>
      <span style={{ width: 16, textAlign: 'center', fontSize: 13, opacity: 0.9 }}>{icon}</span>
      <span style={{ flex: 1 }}>{label}</span>
      {count && <span style={{ font: 'var(--mono-micro)', opacity: 0.55 }}>{count}</span>}
    </button>
  );
}
