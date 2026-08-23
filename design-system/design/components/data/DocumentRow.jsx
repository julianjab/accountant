import React from 'react';
import { StatusBadge } from '../core/StatusBadge.jsx';

export function DocumentRow({ fileName, ext = 'PDF', type, status, time, density = 'dense', indented = false, layout = 'columns', onClick }) {
  const pad = density === 'comfy' ? 'var(--row-pad-comfy)' : 'var(--row-pad-dense)';
  const padding = `${pad} var(--gutter-card) ${pad} ${indented ? '48px' : 'var(--gutter-card)'}`;
  const thumb = (
    <span style={{ width: 22, height: 26, flex: 'none', border: '1px solid var(--color-line-150)', borderRadius: 'var(--radius-xs)', background: 'var(--surface-sunken)', font: '600 8px/26px var(--font-mono)', textAlign: 'center', color: 'var(--text-muted)' }}>{ext}</span>
  );

  if (layout === 'stacked') {
    return (
      <div onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: 12, padding, borderBottom: 'var(--border-row-line)', cursor: onClick ? 'pointer' : 'default' }}>
        {thumb}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ font: 'var(--text-body-strong)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{fileName}</div>
          <div style={{ font: 'var(--text-meta)', color: 'var(--text-muted)', marginTop: 2 }}>{type} · {time}</div>
        </div>
        <StatusBadge status={status} />
      </div>
    );
  }

  return (
    <div onClick={onClick} style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.9fr) minmax(0,1.1fr) auto 90px', alignItems: 'center', padding, borderBottom: 'var(--border-row-line)', cursor: onClick ? 'pointer' : 'default' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
        {thumb}
        <span style={{ font: 'var(--text-body-strong)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{fileName}</span>
      </div>
      <div style={{ font: 'var(--text-small)', color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 10 }}>{type}</div>
      <div style={{ paddingRight: 10 }}><StatusBadge status={status} /></div>
      <div style={{ textAlign: 'right', font: 'var(--mono-meta)', color: 'var(--text-muted)' }}>{time}</div>
    </div>
  );
}
