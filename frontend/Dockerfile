# Multi-stage build - Build stage
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Configure npm registry (optional, use Chinese mirror for faster downloads)
RUN npm config set registry https://registry.npmmirror.com/ || true

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps --no-audit --prefer-offline

# Copy source code
COPY . .

# Build application
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build

# Runtime stage - Use nginx to serve static files
FROM nginx:alpine

# Copy build artifacts
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
