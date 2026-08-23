import React from 'react';
import { Button } from '../../components/core/Button.jsx';
import { Card } from '../../components/core/Card.jsx';
import { Tag } from '../../components/core/Tag.jsx';
import { DocumentRow } from '../../components/data/DocumentRow.jsx';
import { CLIENTS, DOCS } from './data.js';

export function ClientScreen({ index = 0, onOpenDocument }) {
  const c = CLIENTS[index];
  const docs = DOCS.filter(d => d.client === c.name);
  const initials = c.name.split(' ').filter(w => w.length > 2).slice(0, 2).map(w => w[0]).join('').toUpperCase();
  return (
    <div style={{ padding: '30px var(--gutter-page) 44px', maxWidth: 'var(--content-max)' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 24 }}>
        <div style={{ width: 52, height: 52, borderRadius: 13, background: 'var(--surface-deep)', color: 'var(--accent-bright)', font: '600 18px/52px var(--font-sans)', textAlign: 'center' }}>{initials}</div>
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, font: 'var(--text-title)', letterSpacing: 'var(--tracking-display)' }}>{c.name}</h1>
          <div style={{ display: 'flex', gap: 16, marginTop: 6, font: 'var(--text-small)', color: 'var(--text-3)' }}>
            <span style={{ fontFamily: 'var(--font-mono)' }}>{c.taxId}</span>
            <span>{c.email || 'sin correo'}</span>
            <span>Carpeta Drive · Clientes/{c.name}</span>
          </div>
        </div>
        <Button variant="outline">Exportar a hoja de cálculo</Button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 296px', gap: 20, alignItems: 'start' }}>
        <Card padded={false} title="Documentos">
          {docs.map(d => <DocumentRow key={d.name} fileName={d.name} ext={d.ext} type={d.type} status={d.status} time={d.time} layout="stacked" onClick={() => onOpenDocument(d)} />)}
        </Card>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card>
            <div style={{ font: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-muted)', marginBottom: 12 }}>Resumen del mes</div>
            {[['Documentos recibidos', c.docs], ['Filas exportadas', 212], ['Pendientes de revisión', 2]].map(([l, v]) => (
              <div key={l} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '7px 0', borderBottom: '1px solid var(--border-row)' }}>
                <span style={{ font: 'var(--text-small)', color: 'var(--text-2)' }}>{l}</span>
                <span style={{ font: 'var(--mono-value)' }}>{v}</span>
              </div>
            ))}
          </Card>
          <Card tone="deep">
            <div style={{ font: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-on-deep-muted)' }}>Tipos configurados</div>
            <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {['Extracto Bancolombia', 'Factura de venta', 'Recibo de servicios'].map(t => <Tag key={t} tone="onDeep">{t}</Tag>)}
            </div>
            <div style={{ marginTop: 14 }}><Button variant="onDeep" size="sm" fullWidth>Configurar extracción</Button></div>
          </Card>
        </div>
      </div>
    </div>
  );
}
