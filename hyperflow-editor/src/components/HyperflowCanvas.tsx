import { useEffect, useRef, useState } from 'react';
import ReactFlow, { useNodesState, useEdgesState, addEdge, Background, Controls, type Node, type Edge, type OnEdgesChange, type OnNodesChange, type Connection, type ReactFlowInstance } from 'reactflow';
import { useFlowStore } from '../store/flowStore';

type Props = {
  initialNodes: Node[];
  initialEdges: Edge[];
  onChange?: (flow: { nodes: Node[]; edges: Edge[] }) => void;
};

export function HyperflowCanvas({ initialNodes, initialEdges, onChange }: Props) {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { setNodes: storeSetNodes, setEdges: storeSetEdges } = useFlowStore();
  const rfRef = useRef<ReactFlowInstance | null>(null);
  const [pending, setPending] = useState(false);

  const handleConnect = (c: Connection) => setEdges((eds) => addEdge(c, eds));

  useEffect(() => {
    onChange?.({ nodes, edges });
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      if (!pending) return;
      storeSetNodes(nodes);
      storeSetEdges(edges);
      onChange?.({ nodes, edges });
      setPending(false);
    }, 250);
    return () => clearInterval(id);
  }, [pending, nodes, edges, storeSetNodes, storeSetEdges, onChange]);

  const wrappedOnNodesChange: OnNodesChange = (changes) => {
    onNodesChange(changes);
    setPending(true);
  };
  const wrappedOnEdgesChange: OnEdgesChange = (changes) => {
    onEdgesChange(changes);
    setPending(true);
  };

  // removed unused rfProps

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={wrappedOnNodesChange}
        onEdgesChange={wrappedOnEdgesChange}
        onConnect={handleConnect}
        onInit={(inst) => { rfRef.current = inst; }}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default HyperflowCanvas;
