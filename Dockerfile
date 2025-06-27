# Multi-stage Dockerfile for MPLA (Meta-Prompt Learning Agent)
# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/webapp
COPY webapp/package*.json ./
RUN npm ci

COPY webapp/ ./
# Clear any existing node_modules to avoid cross-platform issues
RUN rm -rf node_modules && npm ci
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim AS backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements and install dependencies
COPY mpla_project/requirements.txt ./
COPY server/requirements.txt ./server_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r server_requirements.txt

# Copy the entire application
COPY mpla_project/ ./mpla_project/
COPY server/ ./server/

# Copy built frontend assets
COPY --from=frontend-builder /app/webapp/dist ./server/static/

# Install the MPLA package in development mode
WORKDIR /app/mpla_project
RUN pip install -e .

# Set working directory back to app root
WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash mpla
RUN chown -R mpla:mpla /app
USER mpla

# Expose port 8080 for Endgame compliance
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1

# Start the application
CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8080"] 