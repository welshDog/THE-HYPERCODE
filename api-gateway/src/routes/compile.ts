import { CompileRequestSchema, CompileResponseSchema } from "../schemas/flow";
import { flowHash } from "../lib/hash";
import { buildError } from "../lib/errors";

const FASTAPI_URL = (typeof process !== "undefined" && process.env?.FASTAPI_URL) || "http://127.0.0.1:8000";
const cache = new Map<string, unknown>();

export async function POST(req: Request): Promise<Response> {
  const reqId = (globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2));
  try {
    const json = await req.json();
    const parsed = CompileRequestSchema.safeParse(json);
    if (!parsed.success) {
      const payload = buildError("VALIDATION_FAILED", "Invalid request payload", reqId, { issues: parsed.error.issues });
      return new Response(JSON.stringify(payload), { status: 422, headers: { "content-type": "application/json" } });
    }
    const { flow } = parsed.data;
    const h = flowHash(flow);
    const cached = cache.get(h);
    if (cached) {
      return new Response(JSON.stringify(cached), { status: 200, headers: { "content-type": "application/json" } });
    }

    const idem = `flow-${h}`;
    const res = await fetch(`${FASTAPI_URL}/compile`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-request-id": reqId, "x-idempotency-key": idem },
      body: JSON.stringify(flow)
    });
    if (!res.ok) {
      let detail: unknown;
      try { detail = await res.json(); } catch { detail = { status: res.status }; }
      const payload = buildError("BACKEND_ERROR", "Compiler service error", reqId, { detail });
      return new Response(JSON.stringify(payload), { status: 502, headers: { "content-type": "application/json" } });
    }
    const data = await res.json();
    const parsedResp = CompileResponseSchema.safeParse(data);
    if (!parsedResp.success) {
      const payload = buildError("BACKEND_CONTRACT_ERROR", "Compiler response invalid", reqId, { issues: parsedResp.error.issues });
      return new Response(JSON.stringify(payload), { status: 502, headers: { "content-type": "application/json" } });
    }
    cache.set(h, parsedResp.data);
    return new Response(JSON.stringify(parsedResp.data), { status: 201, headers: { "content-type": "application/json" } });
  } catch (e) {
    const payload = buildError("UNEXPECTED_ERROR", String(e), reqId);
    return new Response(JSON.stringify(payload), { status: 500, headers: { "content-type": "application/json" } });
  }
}
