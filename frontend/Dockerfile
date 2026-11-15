# Stage 1: Build frontend distribution
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests and install packages
COPY package*.json ./
RUN npm ci

# Copy application source and compile static assets
COPY . .
RUN npm run build

# Stage 2: Production web server
FROM nginx:alpine

# Copy custom nginx configuration for SPA routing and API reverse-proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

