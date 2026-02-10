FROM python:3.11-slim

# 1. Install system dependencies
# - pandoc: for markdown conversion
# - libssl-dev, libfontconfig1: required by Tectonic
RUN apt-get update && apt-get install -y \
    pandoc \
    libssl-dev \
    libfontconfig1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Tectonic (Rust-based LaTeX engine)
# This is much smaller and faster than installing texlive-full
RUN wget -qO- https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/

# 3. Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Code
COPY . .

# 5. Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
