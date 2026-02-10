# HyperFlow Editor - Optimized
# Fixed Node version inconsistency, reduced size

# ========================================
# Stage 1: Dependencies
# ========================================
FROM node:20.11-alpine AS deps

WORKDIR /app

# Install dependencies with cache mount
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit

# ========================================
# Stage 2: Builder
# ========================================
FROM node:20.11-alpine AS builder

WORKDIR /app

ENV NODE_ENV=production

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY package.json package-lock.json* ./

# Copy source code
COPY . .

# Build application
RUN npm run build

# ========================================
# Stage 3: Runtime
# ========================================
FROM node:20.11-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder --chown=nextjs:nodejs /app/dist ./dist
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules

USER nextjs

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=20s \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5173/ || exit 1

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0"]
