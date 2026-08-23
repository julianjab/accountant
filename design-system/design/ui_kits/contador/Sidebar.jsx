import React from 'react';
import { SidebarNavItem } from '../../components/navigation/SidebarNavItem.jsx';

const ITEMS = [
  ['queue', '◧', 'Bandeja', '7'],
  ['clients', '◍', 'Clientes', '4'],
  ['types', '⚙', 'Tipos de documento', '5'],
  ['sheets', '▦', 'Hojas de cálculo', '3']
];

export function Sidebar({ screen, onNavigate }) {
  return (
    <nav style={{ width: 'var(--sidebar-width)', flex: 'none', background: 'var(--surface-deep)', color: 'var(--text-on-deep)', display: 'flex', flexDirection: 'column', padding: '22px 14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 8px 22px' }}>
        <div style={{ width: 26, height: 26, borderRadius: 'var(--radius-md)', background: 'var(--accent-bright)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13, color: 'var(--color-green-950)' }}>C</div>
        <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: '-0.01em' }}>Contador</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {ITEMS.map(([id, icon, label, count]) => (
          <SidebarNavItem key={id} icon={icon} label={label} count={count} active={screen === id} onClick={() => onNavigate(id)} />
        ))}
      </div>
      <div style={{ flex: 1 }} />
      <div style={{ borderTop: '1px solid rgba(255,255,255,.09)', padding: '14px 10px 4px' }}>
        <div style={{ font: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-on-deep-muted)', marginBottom: 7 }}>Sesión de Google</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{ width: 26, height: 26, borderRadius: '50%', background: '#1D2B24', border: '1px solid rgba(255,255,255,.1)' }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12.5 }}>julian@estudio.co</div>
            <div style={{ fontSize: 11, color: 'var(--text-on-deep-muted)' }}>Drive · solo lectura</div>
          </div>
        </div>
      </div>
    </nav>
  );
}
