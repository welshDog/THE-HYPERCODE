import { z } from "zod";

export const PositionSchema = z.object({ x: z.number(), y: z.number() });
export const NodeSchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1),
  position: PositionSchema,
  data: z.record(z.any()).optional()
});
export const EdgeSchema = z.object({
  id: z.string().min(1),
  source: z.string().min(1),
  target: z.string().min(1),
  type: z.string().min(1)
});
export const FlowSchema = z.object({
  nodes: z.array(NodeSchema),
  edges: z.array(EdgeSchema),
  viewport: z.record(z.any()).optional()
});

export const CompileOptionsSchema = z.object({
  domain: z.enum(["quantum", "bio"]).optional(),
  idempotencyKey: z.string().optional()
});

export const CompileRequestSchema = z.object({
  flow: FlowSchema,
  options: CompileOptionsSchema.optional()
});

export const SimulationPayloadSchema = z
  .object({
    counts: z.record(z.string(), z.number()).optional()
  })
  .catchall(
    z.object({
      type: z.string(),
      sequence: z.string().optional(),
      efficiency: z.string().optional(),
      off_target_score: z.string().optional(),
      parts: z
        .array(
          z.object({
            label: z.string().optional(),
            seq: z.string(),
            left: z.string().optional(),
            right: z.string().optional()
          })
        )
        .optional(),
      length: z.number().optional(),
      isCircular: z.boolean().optional(),
      log: z.array(z.string()).optional()
    })
  );

export const CompileResponseSchema = z.object({
  success: z.boolean(),
  code: z.string(),
  simulation: z.union([SimulationPayloadSchema, z.record(z.any())]),
  message: z.string(),
  runId: z.string(),
  requestId: z.string()
});

export const ErrorResponseSchema = z.object({
  error: z.object({ code: z.string(), message: z.string(), details: z.record(z.any()).optional() }),
  requestId: z.string()
});

export type Flow = z.infer<typeof FlowSchema>;
export type CompileRequest = z.infer<typeof CompileRequestSchema>;
export type CompileResponse = z.infer<typeof CompileResponseSchema>;
