import React from 'react';
import { Button } from '../../components/core/Button.jsx';
import { Card } from '../../components/core/Card.jsx';
import { Tag } from '../../components/core/Tag.jsx';
import { StatusBadge } from '../../components/core/StatusBadge.jsx';
import { FieldRow } from '../../components/data/FieldRow.jsx';
import { FIELDS_BY_TYPE } from './data.js';

const TIMELINE = [
  ['Archivo detectado en Drive', '18 mar 09:11:42 · webhook', 'var(--text-muted)'],
  ['Clasificado como Extracto Bancolombia', '09:11:49 · claude-classifier', 'var(--status-classifying-fg)'],
  ['OCR completado · 7 campos', '09:12:07 · claude-ocr', 'var(--status-ocr-fg)'],
  ['Listo para aprobación', 'pendiente de revisión manual', 'var(--accent-hover)']
];

export function DocumentScreen({ doc, onBack }) {
  const fields = FIELDS_BY_TYPE[doc.type] || [];
  const avg = fields.length ? (fields.reduce((s, f) => s + f.confidence, 0) / fields.length).toFixed(2) : '—';
  return (
    <div style={{ padding: '22px var(--gutter-page) 40px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <Button variant="outline" size="sm" onClick={onBack}>← Volver</Button>
        <div style={{ fontSize: 14, fontWeight: 600 }}>{doc.name}</div>
        <StatusBadge status={doc.status} />
        <div style={{ flex: 1 }} />
        <Button>Aprobar y enviar a hoja</Button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, alignItems: 'start' }}>
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ font: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-muted)' }}>Documento original</div>
            <div style={{ font: 'var(--mono-micro)', color: 'var(--text-muted)' }}>Drive · 1 de 3</div>
          </div>
          <div style={{ height: 470, border: 'var(--border-dashed)', borderRadius: 'var(--radius-md)', background: 'var(--pattern-placeholder)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ font: 'var(--text-body-strong)', color: 'var(--text-3)' }}>Vista previa del PDF</div>
              <div style={{ font: 'var(--text-meta)', color: 'var(--text-muted)', marginTop: 4 }}>marcador de posición</div>
            </div>
          </div>
        </Card>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card padded={false} title={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>Datos extraídos <Tag tone="accent">{doc.type}</Tag></span>} action={<span style={{ font: 'var(--mono-micro)', color: 'var(--text-muted)' }}>confianza {avg}</span>}>
            {fields.length
              ? fields.map(f => <FieldRow key={f.key} fieldKey={f.key} value={f.value} confidence={f.confidence} />)
              : <div style={{ padding: '18px var(--gutter-card)', font: 'var(--text-small)', color: 'var(--text-3)' }}>No se identificó el tipo de documento, así que no hay campos extraídos.</div>}
          </Card>
          <Card>
            <div style={{ font: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-muted)', marginBottom: 10 }}>Trazabilidad</div>
            {TIMELINE.map(([label, meta, dot]) => (
              <div key={label} style={{ display: 'flex', gap: 11, alignItems: 'flex-start', padding: '5px 0' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', marginTop: 6, flex: 'none', background: dot }} />
                <div>
                  <div style={{ font: 'var(--text-small)' }}>{label}</div>
                  <div style={{ font: 'var(--mono-micro)', color: 'var(--text-muted)', marginTop: 3 }}>{meta}</div>
                </div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  );
}
