FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/dist ./dist
RUN npm i vite
EXPOSE 5173
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD wget -qO- http://localhost:5173/ || exit 1
CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "5173"]
