import React from 'react';

const BASE = {
  fontFamily: 'var(--font-sans)',
  fontWeight: 600,
  borderRadius: 'var(--radius-md)',
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 'var(--space-2)',
  lineHeight: 1.2,
  transition: 'background .12s ease, border-color .12s ease, color .12s ease'
};

const SIZES = {
  sm: { fontSize: 12.5, padding: '6px 11px' },
  md: { fontSize: 13, padding: '8px 14px' },
  lg: { fontSize: 13.5, padding: '10px 16px' }
};

const VARIANTS = {
  solid: { border: 0, background: 'var(--accent)', color: 'var(--color-white)' },
  outline: { border: '1px solid var(--border-strong)', background: 'var(--surface-card)', color: 'var(--text-1)' },
  ghost: { border: 0, background: 'transparent', color: 'var(--text-2)' },
  onDeep: { border: '1px solid rgba(255,255,255,.14)', background: 'transparent', color: 'var(--text-on-deep)' },
  bright: { border: 0, background: 'var(--accent-bright)', color: 'var(--color-green-950)' }
};

export function Button({ variant = 'solid', size = 'md', fullWidth = false, disabled = false, children, ...rest }) {
  const style = { ...BASE, ...SIZES[size], ...VARIANTS[variant] };
  if (fullWidth) { style.width = '100%'; style.justifyContent = 'center'; }
  if (disabled) { style.opacity = 0.45; style.cursor = 'default'; }
  return <button type="button" disabled={disabled} style={style} {...rest}>{children}</button>;
}
