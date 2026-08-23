import React from 'react';
import { Button } from '../../components/core/Button.jsx';

export function Topbar({ crumb }) {
  return (
    <header style={{ flex: 'none', display: 'flex', alignItems: 'center', gap: 16, padding: '0 var(--gutter-page)', height: 'var(--topbar-height)', borderBottom: '1px solid var(--border-default)', background: 'var(--surface-card)' }}>
      <div style={{ font: 'var(--mono-meta)', color: 'var(--text-3)' }}>{crumb}</div>
      <div style={{ flex: 1 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#F2F2EE', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)', padding: '6px 11px', width: 270, color: 'var(--text-muted)', fontSize: 12.5 }}>
        <span>⌕</span><span>Buscar cliente o documento</span>
        <span style={{ marginLeft: 'auto', font: 'var(--mono-micro)', border: '1px solid var(--color-line-150)', borderRadius: 4, padding: '3px 5px' }}>⌘K</span>
      </div>
      <Button>Registrar cliente</Button>
    </header>
  );
}
