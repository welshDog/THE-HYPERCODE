import { useState, useCallback, useRef, useEffect } from 'react';

export type DebugEvent = 
  | { type: 'node_active'; nodeId: string }
  | { type: 'log'; nodeId: string; message: string }
  | { type: 'node_complete'; nodeId: string; result: any }
  | { type: 'execution_complete' }
  | { type: 'error'; message: string };

export function useDebugger() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [completedNodes, setCompletedNodes] = useState<Set<string>>(new Set());
  const [logs, setLogs] = useState<string[]>([]);
  const [results, setResults] = useState<Record<string, any>>({});
  
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    try {
        ws = new WebSocket('ws://localhost:8000/ws/debug');
        
        ws.onopen = () => {
          console.log('Debugger Connected 🔌');
          setIsConnected(true);
        };
        
        ws.onclose = () => {
          console.log('Debugger Disconnected 🔌');
          setIsConnected(false);
        };

        ws.onmessage = (event) => {
          try {
              const data = JSON.parse(event.data) as DebugEvent;
              
              switch (data.type) {
                case 'node_active':
                  setActiveNodeId(data.nodeId);
                  break;
                case 'log':
                  setLogs(prev => [...prev, `[${data.nodeId || 'System'}] ${data.message}`]);
                  break;
                case 'node_complete':
                  setResults(prev => ({ ...prev, [data.nodeId]: data.result }));
                  setCompletedNodes(prev => new Set(prev).add(data.nodeId));
                  // We don't clear activeNodeId immediately, we wait for next active or complete
                  break;
                case 'execution_complete':
                  setIsRunning(false);
                  setActiveNodeId(null);
                  setLogs(prev => [...prev, '✅ Execution Complete']);
                  break;
                case 'error':
                  setLogs(prev => [...prev, `❌ Error: ${data.message}`]);
                  setIsRunning(false);
                  break;
              }
          } catch (e) {
              console.error("Error parsing debug message", e);
          }
        };
        
        socketRef.current = ws;
    } catch (e) {
        console.error("WebSocket connection failed", e);
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const startDebug = useCallback((flowData: any) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setIsRunning(true);
      setLogs(['🚀 Starting Flow State Guardian...']);
      setResults({});
      setCompletedNodes(new Set());
      setActiveNodeId(null);
      socketRef.current.send(JSON.stringify(flowData));
    } else {
      console.error("Debugger not connected");
      setLogs(prev => [...prev, '❌ Error: Debugger not connected. Check backend.']);
    }
  }, []);
  
  const stopDebug = useCallback(() => {
      setIsRunning(false);
      setActiveNodeId(null);
      // Ideally send stop signal to backend if supported
  }, []);

  return {
    isConnected,
    isRunning,
    activeNodeId,
    completedNodes,
    logs,
    results,
    startDebug,
    stopDebug
  };
}
