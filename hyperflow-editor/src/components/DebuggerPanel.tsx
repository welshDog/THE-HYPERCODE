import React, { useState, useEffect, useRef } from 'react';
import './DebuggerPanel.css';

interface DebuggerPanelProps {
  isConnected: boolean;
  isRunning: boolean;
  logs: string[];
  results: Record<string, any>;
  onStart: () => void;
  onStop: () => void;
}

const DebuggerPanel: React.FC<DebuggerPanelProps> = ({
  isConnected,
  isRunning,
  logs,
  results,
  onStart,
  onStop
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className={`debugger-panel ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="debugger-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <div className="debugger-title">
          <span className={`status-dot ${isConnected ? 'online' : ''}`} />
          Flow State Guardian {isRunning ? '(RUNNING)' : ''}
        </div>
        <div>{isCollapsed ? '▲' : '▼'}</div>
      </div>
      
      <div className="debugger-controls">
        {!isRunning ? (
             <button 
             className="btn-debug" 
             onClick={(e) => { e.stopPropagation(); onStart(); }}
             disabled={!isConnected}
           >
             ▶ START DEBUG
           </button>
        ) : (
            <button 
            className="btn-debug btn-stop" 
            onClick={(e) => { e.stopPropagation(); onStop(); }}
          >
            ⏹ STOP
          </button>
        )}
       
      </div>

      <div className="debugger-body" ref={bodyRef}>
        {logs.length === 0 && <div style={{color: '#666', fontStyle: 'italic', padding: '10px'}}>Ready to debug...<br/>Waiting for backend connection...</div>}
        {logs.map((log, i) => (
          <div key={i} className="log-entry" style={{
              color: log.includes('Error') ? '#ff0055' : 
                     log.includes('✅') ? '#00ff9d' : 
                     log.includes('🚀') ? '#00f3ff' : '#ddd'
          }}>
            {log}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DebuggerPanel;
