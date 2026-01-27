import React, { useState, useCallback, useMemo } from 'react';
import { Handle, Position, type NodeProps, useReactFlow } from 'reactflow';
import styles from './SequenceNode.module.css';
import { type SequenceNodeData } from '../engine/BioTypes';

const SequenceNode: React.FC<NodeProps<SequenceNodeData>> = ({ id, data }) => {
  const { setNodes } = useReactFlow();
  const [sequence, setSequence] = useState(data.sequence || '');
  const cleanSeq = useMemo(() => sequence.replace(/\s/g, '').toUpperCase(), [sequence]);
  const isValid = useMemo(() => /^[ATGC]*$/.test(cleanSeq), [cleanSeq]);
  const gcContent = useMemo(() => {
    if (!isValid || cleanSeq.length === 0) return 0;
    const gcCount = (cleanSeq.match(/[GC]/g) || []).length;
    return Math.round((gcCount / cleanSeq.length) * 100);
  }, [isValid, cleanSeq]);

  // Validate and stats calculation
  const pushGraphUpdate = useCallback((nextSeq: string, nextValid: boolean, nextGc: number) => {
    const normalized = nextSeq.replace(/\s/g, '').toUpperCase();
    setNodes((nodes) =>
      nodes.map((node) => {
        if (node.id === id) {
          return {
            ...node,
            data: {
              ...node.data,
              sequence: normalized,
              isValid: nextValid,
              length: normalized.length,
              gcContent: nextGc,
            },
          };
        }
        return node;
      })
    );
  }, [id, setNodes]);

  const handleChange = (evt: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = evt.target.value;
    setSequence(val);
    const normalized = val.replace(/\s/g, '').toUpperCase();
    const valid = /^[ATGC]*$/.test(normalized);
    const gcCount = valid && normalized.length > 0 ? (normalized.match(/[GC]/g) || []).length : 0;
    const nextGc = valid && normalized.length > 0 ? Math.round((gcCount / normalized.length) * 100) : 0;
    pushGraphUpdate(val, valid, nextGc);
  };

  // Initial graph sync from existing data
  useMemo(() => {
    pushGraphUpdate(sequence, isValid, gcContent);
  }, [sequence, isValid, gcContent, pushGraphUpdate]);

  return (
    <div className={`${styles.container} ${!isValid ? styles.error : ''}`}>
      <div className={styles.header}>
        <span className={styles.icon}>🧬</span>
        DNA Sequence
      </div>

      <textarea
        className={`${styles.textarea} ${!isValid ? styles.invalid : ''}`}
        value={sequence}
        onChange={handleChange}
        placeholder="Enter ATGC sequence..."
        spellCheck={false}
      />

      {/* Validation Message */}
      {!isValid && (
        <div className={styles.errorMsg}>
          ⚠️ Invalid Nucleotides Detected
        </div>
      )}

      {/* Stats Panel */}
      <div className={styles.stats}>
        <span>Length: {sequence.replace(/\s/g, '').length} bp</span>
        <span>GC: {gcContent}%</span>
      </div>

      {/* Output Handle (Source) */}
      <Handle
        type="source"
        position={Position.Right}
        id="out"
        className={styles.handle}
      />
    </div>
  );
};

export default SequenceNode;
