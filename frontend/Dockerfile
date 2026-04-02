# Build stage — uses Node 18 + npm 10.x (must match package-lock.json generation for `npm ci`)
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (lockfile must be in sync; if `npm ci` fails after local `npm install`
# with npm 11+, regenerate: docker run --rm -v "$PWD:/app" -w /app node:18-alpine npm install)
RUN npm ci

# Copy source code
COPY . .

# CRA/webpack needs extra heap when bundling large deps (e.g. plotly); default ~2GB OOMs in Docker
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Build the application
RUN DISABLE_ESLINT_PLUGIN=true npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
