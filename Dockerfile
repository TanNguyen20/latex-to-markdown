FROM python:3.11-slim

# 1. Install system dependencies
# - pandoc: for markdown conversion
# - libssl-dev, libfontconfig1: required by Tectonic
# - libgraphite2-3, libharfbuzz0b: REQUIRED to fix your error "libgraphite2.so.3 not found"
RUN apt-get update && apt-get install -y \
    pandoc \
    libssl-dev \
    libfontconfig1 \
    libgraphite2-3 \
    libharfbuzz0b \
    libicu-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Tectonic (Rust-based LaTeX engine)
RUN wget -qO- https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/

# 3. [CRITICAL] Warm up Tectonic
# We compile a tiny file now so Tectonic downloads the base fonts/packages
# into the Docker image. If you skip this, the first user request will be very slow.
RUN echo "\\documentclass{article}\\begin{document}Warmup\\end{document}" > warmup.tex && \
    tectonic warmup.tex && \
    rm warmup.tex warmup.pdf

# 4. Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Code
COPY . .

# 6. Run
# We use 'sh -c' to read the $PORT variable provided by Render.
# If $PORT is missing (e.g. local testing), it defaults to 8000.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
