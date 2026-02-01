import { describe, it, expect } from "vitest";
import { CompileRequestSchema, FlowSchema, CompileResponseSchema } from "../src/schemas/flow";

describe("schemas", () => {
  it("valid flow parses", () => {
    const flow = { nodes: [{ id: "n1", type: "init", position: { x: 0, y: 0 } }], edges: [] };
    const res = FlowSchema.safeParse(flow);
    expect(res.success).toBe(true);
  });

  it("compile request parses", () => {
    const req = { flow: { nodes: [], edges: [] } };
    const res = CompileRequestSchema.safeParse(req);
    expect(res.success).toBe(true);
  });

  it("compile response shape", () => {
    const resp = { success: true, code: "", simulation: {}, message: "ok", runId: "rid", requestId: "req" };
    const res = CompileResponseSchema.safeParse(resp);
    expect(res.success).toBe(true);
  });
});
