import React from 'react';
import { Button } from '../../components/core/Button.jsx';
import { Tag } from '../../components/core/Tag.jsx';
import { CLIENTS, SHEET_ROWS } from './data.js';

const COLS = '110px 1fr 130px 120px 110px';

export function SheetsScreen() {
  const [ix, setIx] = React.useState(0);
  return (
    <div style={{ padding: '30px var(--gutter-page) 44px', maxWidth: 'var(--content-max)' }}>
      <h1 style={{ margin: '0 0 4px', font: 'var(--text-display)', letterSpacing: 'var(--tracking-display)' }}>Hojas de cálculo</h1>
      <div style={{ font: 'var(--text-small)', color: 'var(--text-3)', marginBottom: 22 }}>Una hoja por cliente y periodo: los datos aprobados se acumulan ahí.</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 }}>
        {CLIENTS.map((c, i) => (
          <button key={c.name} type="button" onClick={() => setIx(i)} style={{ textAlign: 'left', cursor: 'pointer', fontFamily: 'var(--font-sans)', border: `1px solid ${i === ix ? 'var(--surface-deep)' : 'var(--border-default)'}`, background: i === ix ? 'var(--surface-deep)' : 'var(--surface-card)', color: i === ix ? 'var(--text-on-deep)' : 'var(--text-1)', borderRadius: 'var(--radius-lg)', padding: '14px 15px' }}>
            <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, font: 'var(--mono-micro)', color: i === ix ? 'var(--text-on-deep-muted)' : 'var(--text-muted)' }}>
              <span>marzo 2026</span><span>{c.docs} docs</span>
            </div>
          </button>
        ))}
      </div>
      <div style={{ background: 'var(--surface-card)', border: 'var(--border-hairline)', borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px var(--gutter-card)', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{CLIENTS[ix].name} · marzo 2026</div>
          <Tag tone="accent">{SHEET_ROWS.length} filas aprobadas</Tag>
          <div style={{ flex: 1 }} />
          <Button variant="outline" size="sm">Abrir en Google Sheets</Button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: COLS, padding: '9px var(--gutter-card)', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-sunken)', font: 'var(--mono-micro)', textTransform: 'uppercase', letterSpacing: '.07em', color: 'var(--text-muted)' }}>
          <div>fecha</div><div>descripcion</div><div>documento</div><div style={{ textAlign: 'right' }}>valor</div><div style={{ textAlign: 'right' }}>iva</div>
        </div>
        {SHEET_ROWS.map(r => (
          <div key={r.date} style={{ display: 'grid', gridTemplateColumns: COLS, padding: 'var(--row-pad-dense) var(--gutter-card)', borderBottom: 'var(--border-row-line)', fontSize: 13 }}>
            <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-3)' }}>{r.date}</div>
            <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 12 }}>{r.desc}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{r.doc}</div>
            <div style={{ textAlign: 'right', font: 'var(--mono-value)' }}>{r.value}</div>
            <div style={{ textAlign: 'right', font: 'var(--mono-meta)', color: 'var(--text-3)' }}>{r.iva}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
