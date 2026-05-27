# Stage 1: Build Core library wheel
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir build

# Copy core package files
COPY packages/core/ /build/packages/core/

# Build timeline-core package wheel
RUN cd packages/core && python -m build --wheel

# Stage 2: Production environment
FROM python:3.12-slim

WORKDIR /workspace

# Copy requirements file first for caching
COPY requirements.txt /workspace/requirements.txt

# Install CLI dependencies and the built timeline-core package
COPY --from=builder /build/packages/core/dist/*.whl /tmp/
RUN pip install --no-cache-dir -r requirements.txt /tmp/*.whl

# Copy CLI app files
COPY app/ /workspace/app/

# Define entrypoint to run the CLI utility
ENTRYPOINT ["python", "app/cli/main.py"]
CMD ["tests/fixtures/sources.valid.yaml"]
