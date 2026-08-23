import React from 'react';
import { StatCard } from '../../components/core/StatCard.jsx';
import { FilterChip } from '../../components/navigation/FilterChip.jsx';
import { ClientGroupHeader } from '../../components/data/ClientGroupHeader.jsx';
import { DocumentRow } from '../../components/data/DocumentRow.jsx';
import { CLIENTS, DOCS } from './data.js';

const FILTERS = ['Todos', 'Pendiente', 'Clasificando', 'OCR', 'Procesado', 'Fallido'];
const LABEL = { pending: 'Pendiente', classifying: 'Clasificando', running_ocr: 'OCR', processed: 'Procesado', failed: 'Fallido' };

export function QueueScreen({ onOpenDocument, onOpenClient }) {
  const [filter, setFilter] = React.useState('Todos');
  const docs = filter === 'Todos' ? DOCS : DOCS.filter(d => LABEL[d.status] === filter);
  const groups = CLIENTS.map((c, i) => ({ client: c.name, index: i, docs: docs.filter(d => d.client === c.name) })).filter(g => g.docs.length);

  return (
    <div style={{ padding: '30px var(--gutter-page) 44px', maxWidth: 'var(--content-max)' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14, marginBottom: 22 }}>
        <h1 style={{ margin: 0, font: 'var(--text-display)', letterSpacing: 'var(--tracking-display)' }}>Bandeja de entrada</h1>
        <div style={{ font: 'var(--text-small)', color: 'var(--text-3)', paddingBottom: 5 }}>Documentos que llegan por Drive, agrupados por cliente.</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 26 }}>
        <StatCard label="Sin procesar" value="3" note="en cola" />
        <StatCard label="Procesados hoy" value="12" note="de 15" tone="accent" />
        <StatCard label="Fallidos" value="1" note="requiere revisión" tone="danger" />
        <StatCard label="Tiempo medio" value="18s" note="por documento" />
      </div>
      <div style={{ background: 'var(--surface-card)', border: 'var(--border-hairline)', borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px var(--gutter-card)', borderBottom: '1px solid var(--border-subtle)' }}>
          {FILTERS.map(f => <FilterChip key={f} label={f} active={filter === f} onClick={() => setFilter(f)} />)}
          <div style={{ flex: 1 }} />
          <div style={{ font: 'var(--text-meta)', color: 'var(--text-muted)' }}>{docs.length} de {DOCS.length} documentos</div>
        </div>
        {groups.map(g => (
          <div key={g.client}>
            <ClientGroupHeader client={g.client} avatarIndex={g.index} count={g.docs.length === 1 ? '1 documento' : g.docs.length + ' documentos'} onClick={() => onOpenClient(g.index)} />
            {g.docs.map(d => <DocumentRow key={d.name} fileName={d.name} ext={d.ext} type={d.type} status={d.status} time={d.time} indented onClick={() => onOpenDocument(d)} />)}
          </div>
        ))}
      </div>
    </div>
  );
}
