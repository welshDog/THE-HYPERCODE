import React from 'react';
import CodeRain from './CodeRain';

interface HyperLayoutProps {
  children: React.ReactNode;
  title?: string;
  status?: string;
}

const HyperLayout: React.FC<HyperLayoutProps> = ({ children, title = "HYPERFLOW EDITOR", status = "ONLINE" }) => {
  return (
    <div className="hc-container">
      <CodeRain />
      <header className="hc-header">
        <h1 className="hc-title">&gt; {title}</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '12px', color: '#666' }}>SYSTEM STATUS:</span>
          <span style={{ color: '#00ff88', fontWeight: 'bold' }}>{status}</span>
          <div style={{
            width: '10px',
            height: '10px',
            background: '#00ff88',
            borderRadius: '50%',
            boxShadow: '0 0 10px #00ff88',
            animation: 'pulse 2s infinite'
          }} />
        </div>
      </header>
      <div style={{ flex: 1, position: 'relative', zIndex: 2, overflow: 'hidden' }}>
        {children}
      </div>
    </div>
  );
};

export default HyperLayout;
