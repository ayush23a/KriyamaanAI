import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatLatency(ms?: number): string {
  if (ms === undefined || ms === null) return '0 ms';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function formatCost(usd?: number | string): string {
  if (usd === undefined || usd === null) return '$0.0000';
  const val = typeof usd === 'string' ? parseFloat(usd) : usd;
  if (isNaN(val)) return '$0.0000';
  if (val < 0.0001 && val > 0) return '<$0.0001';
  return `$${val.toFixed(4)}`;
}

export function formatTokens(tokens?: number): string {
  if (!tokens) return '0';
  if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`;
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
  return tokens.toLocaleString();
}

export function formatDateLabel(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

