import { describe, expect, test, vi } from 'vitest';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HyperflowCanvas } from '../HyperflowCanvas';
import type { Node, Edge } from 'reactflow';

const initialNodes: Node[] = [
  { id: 'a', position: { x: 0, y: 0 }, data: {}, type: 'default' },
  { id: 'b', position: { x: 100, y: 100 }, data: {}, type: 'default' },
];
const initialEdges: Edge[] = [];

describe('HyperflowCanvas', () => {
  test('emits onChange with flow JSON', async () => {
    const spy = vi.fn();
    render(<div style={{ width: 500, height: 400 }}><HyperflowCanvas initialNodes={initialNodes} initialEdges={initialEdges} onChange={spy} /></div>);
    await new Promise((r) => setTimeout(r, 300));
    expect(spy).toHaveBeenCalled();
    const arg = spy.mock.calls[0][0];
    expect(Array.isArray(arg.nodes)).toBe(true);
    expect(Array.isArray(arg.edges)).toBe(true);
  });
});
