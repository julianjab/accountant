export const CLIENTS = [
  { name: 'Ferretería El Tornillo', taxId: '900.412.883-1', email: 'contabilidad@eltornillo.co', docs: 34 },
  { name: 'Panadería La Espiga', taxId: '901.220.554-7', email: 'admin@laespiga.com', docs: 21 },
  { name: 'Transportes Núñez', taxId: '830.005.112-4', email: 'gerencia@tnunez.co', docs: 48 },
  { name: 'Café Altura', taxId: '901.778.201-9', email: null, docs: 12 }
];

export const DOCS = [
  { name: 'extracto-bancolombia-marzo.pdf', ext: 'PDF', client: 'Ferretería El Tornillo', type: 'Extracto Bancolombia', status: 'processed', time: '09:12' },
  { name: 'recibo-servicios-epm.jpg', ext: 'JPG', client: 'Ferretería El Tornillo', type: 'Recibo de servicios', status: 'processed', time: '08:31' },
  { name: 'factura-4821.pdf', ext: 'PDF', client: 'Panadería La Espiga', type: 'Factura de venta', status: 'running_ocr', time: '09:04' },
  { name: 'factura-4820.pdf', ext: 'PDF', client: 'Panadería La Espiga', type: 'Factura de venta', status: 'processed', time: '07:58' },
  { name: 'nomina-marzo.xlsx', ext: 'XLS', client: 'Transportes Núñez', type: 'Nómina', status: 'classifying', time: '08:47' },
  { name: 'escaneo-2026-03-18.pdf', ext: 'PDF', client: 'Café Altura', type: 'Sin identificar', status: 'failed', time: '08:02' },
  { name: 'extracto-davivienda.pdf', ext: 'PDF', client: 'Café Altura', type: 'Extracto bancario', status: 'pending', time: '07:40' }
];

export const FIELDS_BY_TYPE = {
  'Extracto Bancolombia': [
  { key: 'periodo', value: 'Marzo 2026', confidence: 0.99 },
  { key: 'numero_cuenta', value: '****-4821', confidence: 0.97 },
  { key: 'saldo_inicial', value: '$ 12.480.300', confidence: 0.98 },
  { key: 'total_creditos', value: '$ 41.902.115', confidence: 0.95 },
  { key: 'total_debitos', value: '$ 38.774.660', confidence: 0.95 },
  { key: 'saldo_final', value: '$ 15.607.755', confidence: 0.98 },
  { key: 'movimientos', value: '84 registros', confidence: 0.72 }
  ],
  'Extracto bancario': [
    { key: 'periodo', value: 'Marzo 2026', confidence: 0.96 },
    { key: 'numero_cuenta', value: '****-9930', confidence: 0.93 },
    { key: 'saldo_final', value: '$ 3.204.110', confidence: 0.91 }
  ],
  'Recibo de servicios': [
    { key: 'empresa', value: 'EPM', confidence: 0.99 },
    { key: 'periodo', value: 'Marzo 2026', confidence: 0.98 },
    { key: 'valor', value: '$ 318.400', confidence: 0.97 },
    { key: 'fecha_pago', value: '2026-04-05', confidence: 0.88 }
  ],
  'Factura de venta': [
    { key: 'cufe', value: 'a1f9…c204', confidence: 0.94 },
    { key: 'fecha', value: '2026-03-18', confidence: 0.99 },
    { key: 'nit_emisor', value: '900.412.883-1', confidence: 0.97 },
    { key: 'base', value: '$ 892.500', confidence: 0.96 },
    { key: 'iva', value: '$ 169.575', confidence: 0.96 },
    { key: 'total', value: '$ 1.062.075', confidence: 0.98 }
  ],
  'Nómina': [
    { key: 'empleado', value: '12 registros', confidence: 0.85 },
    { key: 'devengado', value: '$ 6.480.220', confidence: 0.9 },
    { key: 'deducciones', value: '$ 812.400', confidence: 0.79 },
    { key: 'neto', value: '$ 5.667.820', confidence: 0.9 }
  ],
  'Sin identificar': []
};

export const FIELDS = FIELDS_BY_TYPE['Extracto Bancolombia'];

export const SHEET_ROWS = [
  { date: '2026-03-02', desc: 'Compra insumos ferretería mayorista', doc: 'factura-4801', value: '1.240.000', iva: '235.600' },
  { date: '2026-03-04', desc: 'Pago servicios EPM marzo', doc: 'recibo-epm', value: '318.400', iva: '0' },
  { date: '2026-03-07', desc: 'Venta mostrador semana 10', doc: 'extracto-banco', value: '4.902.115', iva: '931.401' },
  { date: '2026-03-14', desc: 'Nómina quincena 1', doc: 'nomina-marzo', value: '6.480.220', iva: '0' },
  { date: '2026-03-18', desc: 'Compra herramienta eléctrica', doc: 'factura-4821', value: '892.500', iva: '169.575' }
];
