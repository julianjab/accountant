import React from 'react';
import { Sidebar } from './Sidebar.jsx';
import { Topbar } from './Topbar.jsx';
import { QueueScreen } from './QueueScreen.jsx';
import { ClientScreen } from './ClientScreen.jsx';
import { DocumentScreen } from './DocumentScreen.jsx';
import { SheetsScreen } from './SheetsScreen.jsx';
import { DOCS } from './data.js';

const CRUMBS = { queue: 'inicio / bandeja', clients: 'inicio / clientes', client: 'inicio / clientes', doc: 'inicio / bandeja / documento', sheets: 'inicio / hojas de cálculo', types: 'inicio / configuración / tipos' };

export function App() {
  const [screen, setScreen] = React.useState('queue');
  const [clientIx, setClientIx] = React.useState(0);
  const [doc, setDoc] = React.useState(DOCS[0]);
  const navScreen = screen === 'client' ? 'clients' : screen === 'doc' ? 'queue' : screen;

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--surface-app)', color: 'var(--text-1)', overflow: 'hidden' }}>
      <Sidebar screen={navScreen} onNavigate={s => setScreen(s === 'clients' ? 'client' : s)} />
      <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Topbar crumb={CRUMBS[screen]} />
        <div style={{ flex: 1, overflow: 'auto' }}>
          {screen === 'queue' && <QueueScreen onOpenDocument={d => { setDoc(d); setScreen('doc'); }} onOpenClient={i => { setClientIx(i); setScreen('client'); }} />}
          {screen === 'client' && <ClientScreen index={clientIx} onOpenDocument={d => { setDoc(d); setScreen('doc'); }} />}
          {screen === 'doc' && <DocumentScreen doc={doc} onBack={() => setScreen('queue')} />}
          {screen === 'sheets' && <SheetsScreen />}
          {screen === 'types' && <SheetsScreen />}
        </div>
      </main>
    </div>
  );
}
