# Multi-stage build for GraphRAG API Documentation Platform
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json package-lock.json* ./
RUN npm ci --only=production && npm cache clean --force

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment variables for build
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Generate API documentation
RUN npm run generate-api-docs

# Build the documentation site
RUN npm run build

# Production image, copy all the files and run docusaurus
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 docusaurus

# Copy built application
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/docusaurus.config.js ./docusaurus.config.js

# Copy static assets
COPY --from=builder --chown=docusaurus:nodejs /app/static ./static

# Install serve for production serving
RUN npm install -g serve

USER docusaurus

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Serve the built documentation
CMD ["serve", "-s", "build", "-l", "3000"]
