import React, { useEffect, useMemo, useRef } from 'react';
import { Handle, Position, type NodeProps, useReactFlow, useNodes, useEdges } from 'reactflow';
import styles from './TranslateNode.module.css';
import { type TranslateNodeData, type TranscribeNodeData } from '../engine/BioTypes';

const CODON_TABLE: Record<string, string> = {
  'UUU': 'F', 'UUC': 'F', 'UUA': 'L', 'UUG': 'L',
  'UCU': 'S', 'UCC': 'S', 'UCA': 'S', 'UCG': 'S',
  'UAU': 'Y', 'UAC': 'Y', 'UAA': '*', 'UAG': '*',
  'UGU': 'C', 'UGC': 'C', 'UGA': '*', 'UGG': 'W',
  'CUU': 'L', 'CUC': 'L', 'CUA': 'L', 'CUG': 'L',
  'CCU': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
  'CAU': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
  'CGU': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
  'AUU': 'I', 'AUC': 'I', 'AUA': 'I', 'AUG': 'M',
  'ACU': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
  'AAU': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
  'AGU': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
  'GUU': 'V', 'GUC': 'V', 'GUA': 'V', 'GUG': 'V',
  'GCU': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
  'GAU': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
  'GGU': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
};

const TranslateNode: React.FC<NodeProps<TranslateNodeData>> = ({ id, data }) => {
  const { setNodes } = useReactFlow();
  const nodes = useNodes();
  const edges = useEdges();

  // Source can be TranscribeNode (RNA) or SequenceNode (DNA)
  const sourceNodeData = useMemo(() => {
    const edge = edges.find(e => e.target === id);
    if (!edge) return undefined;
    const node = nodes.find(n => n.id === edge.source);
    return node?.data as TranscribeNodeData | undefined;
  }, [edges, nodes, id]);

  const containerRef = useRef<HTMLDivElement | null>(null);

  const { expectedSequence, expectedIsValid } = useMemo(() => {
    if (sourceNodeData) {
      if (sourceNodeData.isValid === false) {
        return { expectedSequence: '', expectedIsValid: false };
      }

      if (sourceNodeData.sequence) {
        // Normalize to RNA (replace T with U just in case)
        const seq = sourceNodeData.sequence.toUpperCase().replace(/T/g, 'U');

        let protein = '';
        for (let i = 0; i < seq.length; i += 3) {
          const codon = seq.substring(i, i + 3);
          if (codon.length === 3) {
            protein += CODON_TABLE[codon] || '?';
          }
        }
        return { expectedSequence: protein, expectedIsValid: true };
      }
    } else if (!sourceNodeData && data.sequence) {
      return { expectedSequence: '', expectedIsValid: true };
    }

    return { expectedSequence: data.sequence || '', expectedIsValid: true };
  }, [sourceNodeData, data.sequence]);

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
        <span>{isError ? '⚠️' : '🏭'}</span> Translate
      </div>

      <div className={styles.body}>
        <div className={styles.preview}>
          {isError ? 'Upstream Error' : (data.sequence || '')}
        </div>

        <div className={styles.stats}>
          <span>Length: {isError ? 0 : (data.sequence?.length || 0)} aa</span>
          <span>Type: Protein</span>
        </div>
      </div>

      <Handle type="source" position={Position.Right} className={styles.handle} />
    </div>
  );
};

export default TranslateNode;
