/**
 * Layout Component
 * 
 * Main page wrapper with glassmorphism container and 3D background.
 */

import { ReactNode } from 'react';
import { EncryptionMesh } from './EncryptionMesh';

interface LayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  showBranding?: boolean;
}

export function Layout({ 
  children, 
  title = 'DeadDrop',
  subtitle = 'Zero-knowledge file sharing with client-side encryption',
  showBranding = true 
}: LayoutProps) {
  return (
    <>
      <EncryptionMesh />
      <div className="page-container">
        <div className="glass-card">
          {showBranding && (
            <header className="brand-header">
              <div className="brand-logo">
                <LockIcon />
                <h1 className="brand-title">{title}</h1>
              </div>
              <p className="brand-tagline">{subtitle}</p>
            </header>
          )}
          {children}
        </div>
      </div>
    </>
  );
}

// Lock icon SVG component
function LockIcon() {
  return (
    <svg 
      width="32" 
      height="32" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round"
      style={{ color: 'var(--accent-primary)' }}
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

export default Layout;
