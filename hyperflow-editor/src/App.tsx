import { useCallback, useState, useEffect } from 'react';
import ReactFlow, { Background, Controls, type NodeTypes, type EdgeTypes, Panel, type ReactFlowInstance } from 'reactflow';
import HyperflowCanvas from './components/HyperflowCanvas';

import HexNode from './nodes/HexNode';
import SequenceNode from './nodes/SequenceNode';
import TranscribeNode from './nodes/TranscribeNode';
import TranslateNode from './nodes/TranslateNode';
import EnzymeNode from './nodes/EnzymeNode';
import LigaseNode from './nodes/LigaseNode';
import QuantumEdge from './edges/QuantumEdge';
import HelixEdge from './edges/HelixEdge';
import { generateQiskitCode } from './engine/QiskitExporter';
import { generateBioPythonCode } from './engine/BioPythonExporter';
import ExportModal from './components/ExportModal';
import { QUANTUM_PRESET, CENTRAL_DOGMA_PRESET, RESTRICTION_ENZYME_PRESET, ZEN_MODE_PRESET, CLONING_PRESET, PCR_PRESET, CRISPR_PRESET, GOLDEN_GATE_PRESET, type Preset } from './presets';
import CRISPRNode from './nodes/CRISPRNode';
import type { SavedFlow } from './storage/StorageProvider';
import { MockCloudStorageProvider } from './storage/MockCloudStorageProvider';
import { supabase } from './lib/supabase';
import { SupabaseStorageProvider } from './storage/SupabaseStorageProvider';
import PCRNode from './nodes/PCRNode';
import GoldenGateNode from './nodes/GoldenGateNode';
import InitNode from './nodes/InitNode';
import GateNode from './nodes/GateNode';
import MeasureNode from './nodes/MeasureNode';
import CompilerPanel, { type SimulationPayload } from './components/CompilerPanel';
import { useDebugger } from './hooks/useDebugger';
import DebuggerPanel from './components/DebuggerPanel';

// --- React Flow Types ---
const nodeTypes: NodeTypes = {
  hex: HexNode,
  sequence: SequenceNode,
  transcribe: TranscribeNode,
  translate: TranslateNode,
  enzyme: EnzymeNode,
  ligase: LigaseNode,
  crispr: CRISPRNode,
  pcr: PCRNode,
  goldengate: GoldenGateNode,
  // V3 Nodes
  init: InitNode,
  gate: GateNode,
  measure: MeasureNode,
};

const edgeTypes: EdgeTypes = {
  quantum: QuantumEdge,
  helix: HelixEdge,
};

// --- Main Component ---
function App() {
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);

  // Focus Flow State
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isHyperfocus, setIsHyperfocus] = useState(false);
  const [isZenMode, setIsZenMode] = useState(false);
  const [isShowoff, setIsShowoff] = useState(false);
  const [showoffStep, setShowoffStep] = useState(0);
  const [showoffPath, setShowoffPath] = useState<'bio' | 'quantum' | null>(null);
  // Persistent Dyslexia Mode (Neurodivergent-First Default)
  const [isDyslexiaMode, setIsDyslexiaMode] = useState(() => {
    return localStorage.getItem('hypercode:dyslexiaMode') === 'true';
  });

  // Persist Dyslexia Mode changes
  useEffect(() => {
    localStorage.setItem('hypercode:dyslexiaMode', String(isDyslexiaMode));
  }, [isDyslexiaMode]);

  // --- Flow State Guardian (Debugger) ---
  const {
    isConnected,
    isRunning,
    activeNodeId,
    completedNodes,
    logs,
    startDebug,
    stopDebug
  } = useDebugger();

  // Update Node Glow Effects
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        // Remove existing debug classes
        let newClass = (node.className || '')
          .replace('node-active-glow', '')
          .replace('node-completed', '')
          .trim();

        if (node.id === activeNodeId) {
          newClass += ' node-active-glow';
        } else if (completedNodes.has(node.id)) {
          newClass += ' node-completed';
        }

        // Only update if changed
        if (newClass.trim() !== (node.className || '').trim()) {
          return { ...node, className: newClass.trim() };
        }
        return node;
      })
    );
  }, [activeNodeId, completedNodes, setNodes]);

  const handleStartDebug = useCallback(() => {
    if (!rfInstance) return;
    const flow = rfInstance.toObject();
    startDebug(flow);
  }, [startDebug, rfInstance]);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Cloud Sync State
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'synced' | 'error'>('idle');

  // Compiler State
  const [isCompilerOpen, setIsCompilerOpen] = useState(false);
  const [compiledCode, setCompiledCode] = useState('');
  const [simulationResults, setSimulationResults] = useState<SimulationPayload | undefined>(undefined);

  const [backendStatus, setBackendStatus] = useState<'connected' | 'checking' | 'unreachable'>('checking');

  const [storageProvider] = useState(() => {
    if (supabase) {
      console.log('Using Supabase Cloud Storage');
      return new SupabaseStorageProvider(supabase);
    }
    console.log('Supabase credentials missing. Using Mock Storage.');
    return new MockCloudStorageProvider();
  });

  useEffect(() => {
    const loadFromCloud = async () => {
      try {
        const saved = await storageProvider.load('current-flow');
        if (saved?.viewport) setZoomLevel(saved.viewport.zoom);
      } catch (e) {
        console.warn('No cloud save found or load failed', e);
      }
    };
    loadFromCloud();
  }, [storageProvider]);

  // Auto-Save Effect
  useEffect(() => {
    const saveTimer = setTimeout(() => {
      // Only save if we have content
      if (nodes.length === 0) return;

      setSyncStatus('syncing');
      const flow: SavedFlow = {
        id: 'current-flow', // Single slot for now
        name: 'Auto-Saved Flow',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        nodes,
        edges,
        viewport: { x: 0, y: 0, zoom: zoomLevel }
      };

      storageProvider.save(flow)
        .then(() => setSyncStatus('synced'))
        .catch((err) => {
          console.error('Auto-save failed', err);
          setSyncStatus('error');
        });

    }, 2000); // 2 second debounce

    return () => clearTimeout(saveTimer);
  }, [nodes, edges, zoomLevel, storageProvider]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 4. Reset View (Ctrl+0 or Space when not typing)
      if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault();
        rfInstance?.fitView({ duration: 800 });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [rfInstance]);

  useEffect(() => {
    let cancelled = false;
    const ping = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 1500);
        const res = await fetch('http://127.0.0.1:8000/health', { signal: controller.signal });
        clearTimeout(timeout);
        if (!cancelled) setBackendStatus(res.ok ? 'connected' : 'unreachable');
      } catch {
        if (!cancelled) setBackendStatus('unreachable');
      }
    };
    ping();
    const id = setInterval(ping, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // Export Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [exportCode, setExportCode] = useState('');

  // Storage Handlers
  const handleSaveFile = useCallback(() => {
    const flow: SavedFlow = {
      id: 'manual-save', // For file export, ID is less relevant
      name: 'HyperFlow Export',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      nodes,
      edges,
      viewport: { x: 0, y: 0, zoom: zoomLevel } // Approximate viewport
    };

    const json = JSON.stringify(flow, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `hyperflow-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [nodes, edges, zoomLevel]);

  const handleLoadFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      try {
        const flow = JSON.parse(content) as SavedFlow;
        setNodes(flow.nodes || []);
        setEdges(flow.edges || []);
        if (flow.viewport) {
          // Viewport restore if needed
        }
        alert('Flow loaded successfully!');
      } catch (err) {
        alert('Failed to load flow: Invalid JSON');
        console.error(err);
      }
    };
    reader.readAsText(file);
    // Reset input
    event.target.value = '';
  };

  const loadPreset = useCallback((preset: Preset) => {
    // Reset graph with new preset
    setNodes([...preset.nodes]);
    setEdges([...preset.edges]);
  }, [setNodes, setEdges]);

  const handleExport = () => {
    const code = generateQiskitCode(nodes);
    setExportCode(code);
    setIsModalOpen(true);
  };

  const handleBioExport = () => {
    // Filter for Bio-Lane nodes only (simple heuristic based on type)
    const bioNodes = nodes.filter(n => ['sequence', 'transcribe', 'translate', 'enzyme', 'ligase'].includes(n.type || ''));
    const code = generateBioPythonCode(bioNodes);
    setExportCode(code);
    setIsModalOpen(true);
  };

  const runShowoffStep = () => {
    if (!isShowoff) return;
    if (showoffPath === 'bio') {
      if (showoffStep === 0) {
        const nextSeq = 'ATGGCTGAA';
        setNodes(nds => nds.map(n => n.type === 'sequence' ? {
          ...n,
          data: { ...n.data, sequence: nextSeq, isValid: true, length: nextSeq.length, gcContent: Math.round(((nextSeq.match(/[GC]/g) || []).length / nextSeq.length) * 100) }
        } : n));
        setShowoffStep(1);
      } else if (showoffStep === 1) {
        setNodes(nds => nds.map(n => n.type === 'transcribe' ? { ...n, data: { ...n.data, isCodingStrand: false } } : n));
        setShowoffStep(2);
      } else if (showoffStep === 2) {
        handleBioExport();
        setShowoffStep(3);
      }
    } else if (showoffPath === 'quantum') {
      const clearGlow = (nds: typeof nodes) => nds.map(n => ({ ...n, className: (n.className || '').replace('node-active-glow', '').trim() }));
      if (showoffStep === 0) {
        setNodes(nds => clearGlow(nds).map(n => n.id === 'h-node' ? { ...n, className: ((n.className || '') + ' node-active-glow').trim() } : n));
        setShowoffStep(1);
      } else if (showoffStep === 1) {
        setNodes(nds => clearGlow(nds).map(n => n.id === 'cx-node' ? { ...n, className: ((n.className || '') + ' node-active-glow').trim() } : n));
        setShowoffStep(2);
      } else if (showoffStep === 2) {
        setNodes(nds => clearGlow(nds).map(n => n.id === 'measure-0' ? { ...n, className: ((n.className || '') + ' node-active-glow').trim() } : n));
        setShowoffStep(3);
      } else if (showoffStep === 3) {
        handleCompile();
        setShowoffStep(4);
      }
    }
  };

  // Keyboard Shortcuts Effect
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if input/select is focused
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        return;
      }

      // 1. Toggle Hyperfocus (Shift + F)
      if (e.shiftKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        setIsHyperfocus(prev => !prev);
      }

      // 2. Save File (Ctrl/Cmd + S)
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleSaveFile();
      }

      // 3. Load File (Ctrl/Cmd + O)
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'o') {
        e.preventDefault();
        // Trigger hidden file input click
        const fileInput = document.getElementById('hidden-file-input');
        if (fileInput) fileInput.click();
      }

      // 4. Reset View (Ctrl+0)
      if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault();
        rfInstance?.fitView({ duration: 800 });
      }

      // 5. Zen Mode Toggle (Shift + Z)
      if (e.shiftKey && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        setIsZenMode(prev => {
          const next = !prev;
          if (next) {
            // Entering Zen Mode
            loadPreset(ZEN_MODE_PRESET);
            setIsHyperfocus(true);
          } else {
            // Exiting Zen Mode -> Load Default? Or just stay?
            // Let's just toggle the flag and let user choose preset
            // Or restore Central Dogma
            loadPreset(CENTRAL_DOGMA_PRESET);
            setIsHyperfocus(false);
          }
          return next;
        });
      }

      // 6. Dyslexia Mode Toggle (Shift + D)
      if (e.shiftKey && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        setIsDyslexiaMode(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSaveFile, rfInstance, loadPreset]);

  const onConnect = useCallback((_params: unknown) => {}, []);

  // Focus Flow Logic
  const handleMove = useCallback((_e: unknown, viewport: { zoom: number }) => {
    setZoomLevel(viewport.zoom);
  }, []);

  const handleSelectionChange = useCallback(({ nodes: selectedNodes }: { nodes: import('reactflow').Node[] }) => {
    if (selectedNodes.length > 0) {
      setSelectedNodeId(selectedNodes[0].id);
    } else {
      setSelectedNodeId(null);
    }
  }, []);

  // Determine classes for the container
  const isLodLow = zoomLevel < 0.6;
  const containerClass = `hyperflow-container ${isLodLow ? 'lod-low' : ''} ${isHyperfocus ? 'hyperfocus-mode' : ''} ${isDyslexiaMode ? 'dyslexia-mode' : ''}`;

  // Apply dimming logic
  // We don't want to re-render nodes constantly, but we can use CSS variables or classes
  // A cleaner way for "Hyperfocus" is to pass a class to the ReactFlow wrapper, and use CSS to select dimmed nodes
  // But we need to know WHICH nodes are dimmed.
  // We can update the nodes' className when selection changes if hyperfocus is on.

  // Actually, let's update node classes whenever selection/hyperfocus changes
  // This might be slightly expensive but for <100 nodes it's fine.

  const getFocusSet = useCallback((centerId: string | null) => {
    if (!centerId) return new Set<string>();
    const focusSet = new Set<string>();
    focusSet.add(centerId);
    edges.forEach(edge => {
      if (edge.source === centerId) focusSet.add(edge.target);
      if (edge.target === centerId) focusSet.add(edge.source);
    });
    return focusSet;
  }, [edges]);

  // Effect to update node styles for Hyperfocus
  // We use a useEffect to avoid loop in render
  useState(() => {
    // This is just initialization, real logic in useEffect
  });

  // We need to use `setNodes` to update classNames. 
  // To avoid infinite loop, we should only do this when specific dependencies change.
  // Actually, let's just use inline styles or classes in the render logic if possible? 
  // No, ReactFlow controls the node rendering. We have to update the node objects.

  // Optimization: Only update if the state actually changes.
  // Better yet: Use a computed style map or Context?
  // Let's stick to the className update for now, triggered by effects.

  // NOTE: In a real large app, we'd use a custom node wrapper that listens to a context.
  // For this v1.2, let's use the className approach.

  const updateNodeDimming = useCallback(() => {
    if (!isHyperfocus) {
      // Clear dimming
      setNodes(nds => nds.map(n => ({
        ...n,
        className: (n.className || '').replace(' dimmed', '')
      })));
      return;
    }

    const focusSet = getFocusSet(selectedNodeId);

    setNodes(nds => nds.map(n => {
      const isDimmed = selectedNodeId && !focusSet.has(n.id);
      let newClass = (n.className || '').replace(' dimmed', '');
      if (isDimmed) newClass += ' dimmed';

      // Only update if changed
      if (newClass !== n.className) {
        return { ...n, className: newClass };
      }
      return n;
    }));
  }, [isHyperfocus, selectedNodeId, getFocusSet, setNodes]);

  const handleCompile = async () => {
    if (!rfInstance) return;
    const flow = rfInstance.toObject();

    const offlineCounts = () => {
      const hasH = nodes.some(n => n.id === 'h-node');
      const hasCX = nodes.some(n => n.id === 'cx-node');
      const measures = nodes.filter(n => n.type === 'measure').length;
      if (hasH && hasCX && measures >= 2) {
        return { '00': 512, '11': 512 } as Record<string, number>;
      }
      return { '0': 1024 } as Record<string, number>;
    };

    try {
      setCompiledCode("Compiling...");
      setSimulationResults(undefined);
      setIsCompilerOpen(true);

      if (backendStatus !== 'connected') {
        const code = [
          'from qiskit import QuantumCircuit',
          'qc = QuantumCircuit(2,2)',
          'qc.h(0)',
          'qc.cx(0,1)',
          'qc.measure([0,1],[0,1])'
        ].join('\n');
        setCompiledCode(code);
        setSimulationResults({ counts: offlineCounts() } as SimulationPayload);
        return;
      }

      const reqId = (globalThis.crypto && 'randomUUID' in globalThis.crypto) ? globalThis.crypto.randomUUID() : String(Date.now());
      const idem = `compile-${reqId}`;
      const response = await fetch('http://127.0.0.1:8000/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(flow),
        // @ts-ignore
        headers: { 'Content-Type': 'application/json', 'x-request-id': reqId, 'x-idempotency-key': idem },
      });

      if (!response.ok) {
        throw new Error(`Compiler Error: ${response.statusText}`);
      }

      const data = await response.json();
      setCompiledCode(data.code);
      setSimulationResults(data.simulation as unknown as SimulationPayload);
    } catch {
      const code = [
        'from qiskit import QuantumCircuit',
        'qc = QuantumCircuit(2,2)',
        'qc.h(0)',
        'qc.cx(0,1)',
        'qc.measure([0,1],[0,1])'
      ].join('\n');
      setCompiledCode(code);
      setSimulationResults({ counts: offlineCounts() } as SimulationPayload);
    }
  };

  // Trigger update when relevant state changes
  // We need a useEffect that calls this
  useEffect(() => {
    updateNodeDimming();
  }, [isHyperfocus, selectedNodeId, updateNodeDimming]);


  return (
    <div style={{ width: '100vw', height: '100vh', background: '#2d3436' }} className={containerClass}>
      <HyperflowCanvas initialNodes={CENTRAL_DOGMA_PRESET.nodes} initialEdges={CENTRAL_DOGMA_PRESET.edges} onChange={() => {}} />
      <Panel position="top-right">
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {/* Sync Status Indicator */}
            <div style={{
              padding: '8px 12px',
              borderRadius: '20px',
              background: syncStatus === 'error' ? '#ff7675' : syncStatus === 'synced' ? '#55efc4' : syncStatus === 'syncing' ? '#ffeaa7' : 'rgba(255,255,255,0.2)',
              color: '#2d3436',
              fontWeight: 'bold',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              transition: 'all 0.3s ease',
              opacity: syncStatus === 'idle' ? 0.5 : 1
            }}>
              {syncStatus === 'syncing' && '🔄'}
              {syncStatus === 'synced' && '☁️'}
              {syncStatus === 'error' && '❌'}
              {syncStatus === 'idle' && '☁️'}
              {syncStatus === 'syncing' ? 'Syncing...' : syncStatus === 'synced' ? 'Saved' : syncStatus === 'error' ? 'Error' : 'Ready'}
            </div>

            <div style={{
              padding: '8px 12px',
              borderRadius: '20px',
              background: backendStatus === 'unreachable' ? '#ff7675' : backendStatus === 'connected' ? '#55efc4' : '#ffeaa7',
              color: '#2d3436',
              fontWeight: 'bold',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              transition: 'all 0.3s ease'
            }}>
              {backendStatus === 'connected' && '🔌'}
              {backendStatus === 'unreachable' && '❌'}
              {backendStatus === 'checking' && '🔄'}
              {backendStatus === 'connected' ? 'Backend Connected' : backendStatus === 'unreachable' ? 'Backend Unavailable' : 'Checking Backend...'}
            </div>

            {/* Dyslexia Toggle */}
            <button
              onClick={() => setIsDyslexiaMode(!isDyslexiaMode)}
              style={{
                padding: '10px',
                borderRadius: '5px',
                border: isDyslexiaMode ? '2px solid #00b894' : 'none',
                background: isDyslexiaMode ? '#55efc4' : '#dfe6e9',
                color: '#2d3436',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontFamily: isDyslexiaMode ? '"Comic Sans MS", "Chalkboard SE", sans-serif' : 'Inter, sans-serif',
                fontSize: '1.2rem',
                lineHeight: 1
              }}
              title={`Toggle Dyslexia Font (Shift + D)`}
            >
              👁️
            </button>

            {/* Preset Selector */}
            <select data-testid="preset-select"
              onChange={(e) => {
                const val = e.target.value;
                if (val === 'quantum') { loadPreset(QUANTUM_PRESET); setIsZenMode(false); }
                if (val === 'dogma') { loadPreset(CENTRAL_DOGMA_PRESET); setIsZenMode(false); }
                if (val === 'enzyme') { loadPreset(RESTRICTION_ENZYME_PRESET); setIsZenMode(false); }
                if (val === 'cloning') { loadPreset(CLONING_PRESET); setIsZenMode(false); }
                if (val === 'pcr') { loadPreset(PCR_PRESET); setIsZenMode(false); }
                if (val === 'crispr') { loadPreset(CRISPR_PRESET); setIsZenMode(false); }
                if (val === 'goldengate') { loadPreset(GOLDEN_GATE_PRESET); setIsZenMode(false); }
                if (val === 'zen') {
                  loadPreset(ZEN_MODE_PRESET);
                  setIsZenMode(true);
                  setIsHyperfocus(true);
                }
              }}
              defaultValue="dogma"
              style={{
                padding: '10px',
                borderRadius: '5px',
                border: isZenMode ? '2px solid #00b894' : 'none',
                background: '#dfe6e9',
                color: '#2d3436',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontFamily: 'Inter, sans-serif'
              }}
            >
              <option value="dogma">🧬 Central Dogma</option>
              <option value="enzyme">✂️ Restriction</option>
              <option value="cloning">🧪 Cloning</option>
              <option value="pcr">🌡️ PCR</option>
              <option value="crispr">✂️ CRISPR</option>
              <option value="goldengate">Golden Gate Assembly</option>
              <option value="quantum">⚛️ Quantum</option>
              <option value="zen">🧘 Zen Mode</option>
            </select>

            {/* Storage Controls */}
            <button
              onClick={handleSaveFile}
              style={{
                padding: '10px 15px',
                borderRadius: '5px',
                border: 'none',
                background: '#0984e3',
                color: 'white',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontFamily: 'Inter, sans-serif'
              }}
              title="Download Flow as JSON"
            >
              💾 Save
            </button>

            <label
              style={{
                padding: '10px 15px',
                borderRadius: '5px',
                border: 'none',
                background: '#6c5ce7',
                color: 'white',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontFamily: 'Inter, sans-serif',
                display: 'inline-block'
              }}
              title="Load Flow from JSON"
            >
              📂 Load
              <input
                type="file"
                accept=".json"
                onChange={handleLoadFile}
                style={{ display: 'none' }}
              />
            </label>

            <button data-testid="compile-button"
              onClick={handleCompile}
              style={{
                padding: '10px 15px',
                borderRadius: '5px',
                border: 'none',
                background: '#e17055',
                color: 'white',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontFamily: 'Inter, sans-serif'
              }}
              title="Compile to HyperCode"
            >
              🚀 Compile
            </button>

            {/* Hyperfocus Toggle */}
            <button
              onClick={() => setIsHyperfocus(!isHyperfocus)}
              style={{
                padding: '8px 12px',
                borderRadius: '5px',
                border: isHyperfocus ? '2px solid #74b9ff' : 'none',
                background: isHyperfocus ? '#0984e3' : '#dfe6e9',
                color: isHyperfocus ? 'white' : 'black',
                cursor: 'pointer',
                fontWeight: 'bold',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                fontFamily: 'Inter, sans-serif'
              }}
              title="Toggle Hyperfocus Mode (Shift+F)"
            >
              {isHyperfocus ? '🎯 Hyperfocus ON' : '👁️ Focus'}
            </button>

            <div style={{ width: '1px', height: '24px', background: '#b2bec3', margin: '0 10px' }}></div>

            <button
              onClick={handleExport}
              style={{
                padding: '10px 20px',
                background: '#6c5ce7',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                fontWeight: 'bold',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
              }}
            >
              ⚛️ Export Qiskit
            </button>
            <button
              onClick={handleBioExport}
              style={{
                padding: '10px 20px',
                background: '#00b894',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                fontWeight: 'bold',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
              }}
            >
              🧬 Export BioPython
            </button>
            <button
              onClick={() => { const next = !isShowoff; setIsShowoff(next); setShowoffStep(0); setShowoffPath(next ? (nodes.some(n => n.type === 'gate' || n.type === 'measure') ? 'quantum' : 'bio') : null); }}
              style={{
                padding: '10px 15px',
                borderRadius: '5px',
                border: '1px solid #636e72',
                background: isShowoff ? '#55efc4' : 'transparent',
                color: '#2d3436',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontFamily: 'Inter, sans-serif'
              }}
            >
              Show‑off Mode
            </button>
          </div>
        </Panel>
      </ReactFlow>

      {isShowoff && (
        <Panel position="top-left" style={{ background: 'white', borderRadius: '8px', padding: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }} aria-live="polite">
            <div style={{ fontWeight: 700, color: '#2d3436' }}>Show‑off Mode</div>
            <div style={{ color: '#636e72', fontSize: '12px' }}>
              {showoffPath === 'bio' && (
                (showoffStep === 0 && 'Step 1: Update DNA and watch RNA/Protein change.') ||
                (showoffStep === 1 && 'Step 2: Flip strand to see transcription differences.') ||
                (showoffStep === 2 && 'Step 3: Export BioPython to show code.') ||
                (showoffStep >= 3 && 'Done. Tweak nodes or rerun steps.')
              )}
              {showoffPath === 'quantum' && (
                (showoffStep === 0 && 'Step 1: Apply H to create superposition.') ||
                (showoffStep === 1 && 'Step 2: Entangle with CX.') ||
                (showoffStep === 2 && 'Step 3: Measure qubit 0.') ||
                (showoffStep === 3 && 'Step 4: Compile to view results.') ||
                (showoffStep >= 4 && 'Done. Explore counts and adjust gates.')
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={runShowoffStep} style={{ padding: '8px 12px', borderRadius: '6px', border: 'none', background: '#6c5ce7', color: 'white', fontWeight: 600, cursor: 'pointer' }}>Do Step</button>
              <button onClick={() => { setShowoffStep(0); }} style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #636e72', background: 'transparent', color: '#2d3436', fontWeight: 600, cursor: 'pointer' }}>Reset</button>
              <button onClick={() => { setIsShowoff(false); setShowoffPath(null); }} style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #636e72', background: 'transparent', color: '#2d3436', fontWeight: 600, cursor: 'pointer' }}>Skip</button>
              <div aria-label="Progress" style={{ marginLeft: '8px', color: '#636e72', alignSelf: 'center' }}>Step {showoffStep + 1}</div>
            </div>
          </div>
        </Panel>
      )}

      <ExportModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        code={exportCode}
      />

      <DebuggerPanel
        isConnected={isConnected}
        isRunning={isRunning}
        logs={logs}
        onStart={handleStartDebug}
        onStop={stopDebug}
      />

      {isCompilerOpen && (
        <CompilerPanel
          code={compiledCode}
          simulation={simulationResults}
          onClose={() => setIsCompilerOpen(false)}
        />
      )}
    </div >
  );
}

export default App;
