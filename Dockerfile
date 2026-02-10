FROM python:3.11-slim

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    pandoc \
    libssl-dev \
    libfontconfig1 \
    libgraphite2-3 \
    libharfbuzz0b \
    libicu-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Tectonic
RUN wget -qO- https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/

WORKDIR /app

# 3. FIX: Copy the local warmup.tex file instead of using 'echo'
# This prevents the "invalid character" error.
COPY warmup.tex .
RUN tectonic warmup.tex && \
    rm warmup.tex warmup.pdf

# 4. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Application Code
COPY . .

# 6. Start App
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
