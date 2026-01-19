# Multi-stage build: Build frontend, then create final image with both

# Stage 1: Build the SvelteKit frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/web

# Copy package files and install dependencies
COPY web/package*.json ./
RUN npm ci

# Copy web source and build
COPY web/ ./
RUN npm run build

# Stage 2: Final image with Python backend + built frontend
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python source code
COPY src/ ./src/

# Copy data files (use a shell to handle missing directories gracefully)
RUN mkdir -p ./data
COPY data/ ./data/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/web/build ./web/build

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8000

# Run the server (use shell form to expand $PORT)
CMD python -m uvicorn centuria.api.server:app --host 0.0.0.0 --port ${PORT:-8000}
