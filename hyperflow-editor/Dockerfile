
# ========================================
# Stage 1: Dependencies
# ========================================
FROM node:18-alpine AS deps
WORKDIR /app
# Copy package.json and optional package-lock.json
COPY package.json package-lock.json* ./
RUN npm ci

# ========================================
# Stage 2: Builder
# ========================================
FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ========================================
# Stage 3: Runtime
# ========================================
FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production 

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules

USER nextjs

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD wget -qO- http://localhost:5173/ >/dev/null || exit 1
CMD ["npm", "run", "preview", "--", "--host"]
