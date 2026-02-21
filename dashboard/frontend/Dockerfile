# =============================================================================
# Development Dockerfile for Next.js with Hot Reload
# =============================================================================

FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Run in dev mode with hot reload
CMD ["npm", "run", "dev"]
