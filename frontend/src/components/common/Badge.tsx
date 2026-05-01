/**
 * Badge 组件
 */

import { clsx } from 'clsx';
import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
}

export function Badge({ children, variant = 'default', size = 'sm' }: BadgeProps) {
  const variants = {
    default: 'bg-slate-700 text-slate-300',
    success: 'bg-green-500/20 text-green-400 border border-green-500/50',
    warning: 'bg-amber-500/20 text-amber-400 border border-amber-500/50',
    danger: 'bg-red-500/20 text-red-400 border border-red-500/50',
    info: 'bg-blue-500/20 text-blue-400 border border-blue-500/50',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        variants[variant],
        sizes[size]
      )}
    >
      {children}
    </span>
  );
}
