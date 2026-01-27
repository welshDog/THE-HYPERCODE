import React, { useEffect, useMemo, useRef } from 'react';
import { Handle, Position, type NodeProps, useReactFlow, useNodes, useEdges } from 'reactflow';
import styles from './TranscribeNode.module.css';
import { type TranscribeNodeData, type SequenceNodeData } from '../engine/BioTypes';

const TranscribeNode: React.FC<NodeProps<TranscribeNodeData>> = ({ id, data }) => {
  const { setNodes } = useReactFlow();
  const nodes = useNodes();
  const edges = useEdges();

  // 1. Find the connected source node
  // In v11, we manually filter edges and nodes
  const sourceNodeData = useMemo(() => {
    const edge = edges.find(e => e.target === id);
    if (!edge) return undefined;
    const node = nodes.find(n => n.id === edge.source);
    return node?.data as SequenceNodeData | undefined;
  }, [edges, nodes, id]);

  const containerRef = useRef<HTMLDivElement | null>(null);

  // 2. Reactive Logic: Compute RNA when DNA source changes
  const { expectedSequence, expectedIsValid } = useMemo(() => {
    if (sourceNodeData) {
      // Check upstream validity
      if (sourceNodeData.isValid === false) {
        return { expectedSequence: '', expectedIsValid: false };
      }

      if (sourceNodeData.sequence) {
        const dna = sourceNodeData.sequence;
        let rna = '';

        // Handle Strand Selection
        if (data.isCodingStrand === false) {
          // Template Strand: Complement then replace T->U
          rna = dna.split('').map(base => {
            switch (base) {
              case 'A': return 'U';
              case 'T': return 'A';
              case 'G': return 'C';
              case 'C': return 'G';
              default: return base;
            }
          }).join('');
        } else {
          // Coding Strand (Default): Just replace T->U
          rna = dna.replace(/T/g, 'U');
        }
        return { expectedSequence: rna, expectedIsValid: true };
      }
    } else if (!sourceNodeData && data.sequence) {
      // Reset if disconnected
      return { expectedSequence: '', expectedIsValid: true };
    }

    // Default: keep current if no source but also no sequence (initial state)
    // Or if source exists but has no sequence yet
    return { expectedSequence: data.sequence || '', expectedIsValid: true };
  }, [sourceNodeData, data.isCodingStrand, data.sequence]);

  useEffect(() => {
    const needsUpdate = data.sequence !== expectedSequence || data.isValid !== expectedIsValid;

    if (needsUpdate) {
      if (data.sequence !== expectedSequence && expectedIsValid && expectedSequence !== '' && containerRef.current) {
        containerRef.current.classList.add(styles.pulse);
        setTimeout(() => containerRef.current && containerRef.current.classList.remove(styles.pulse), 600);
      }

      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === id) {
            return {
              ...node,
              data: {
                ...node.data,
                sequence: expectedSequence,
                isValid: expectedIsValid,
              },
            };
          }
          return node;
        })
      );
    }
  }, [expectedSequence, expectedIsValid, data.sequence, data.isValid, id, setNodes]);

  const isError = data.isValid === false;

  return (
    <div ref={containerRef} className={`${styles.container} ${isError ? styles.error : ''}`}>
      <Handle type="target" position={Position.Left} className={styles.handle} />

      <div className={styles.header}>
        <span>{isError ? '⚠️' : '🌫️'}</span> Transcribe
      </div>

      <div className={styles.body}>
        <div className={styles.row}>
          <label className={styles.label}>Strand:</label>
          <select
            className={styles.select}
            value={data.isCodingStrand !== false ? 'coding' : 'template'}
            onChange={(e) => {
              const isCoding = e.target.value === 'coding';
              setNodes(nds => nds.map(n => {
                if (n.id === id) {
                  return { ...n, data: { ...n.data, isCodingStrand: isCoding } };
                }
                return n;
              }));
            }}
          >
            <option value="coding">Coding (5'→3')</option>
            <option value="template">Template (3'→5')</option>
          </select>
        </div>

        <div className={styles.preview}>
          {isError ? 'Upstream Error' : (data.sequence || '')}
        </div>

        <div className={styles.stats}>
          <span>Length: {isError ? 0 : (data.sequence?.length || 0)} nt</span>
          <span>Type: mRNA</span>
        </div>
      </div>

      <Handle type="source" position={Position.Right} className={styles.handle} />
    </div>
  );
};

export default TranscribeNode;
