FROM python:3.11-slim

# 1. Enable 'contrib' and 'non-free' repos for Microsoft Fonts
# We edit the source list directly to avoid "software-properties-common" errors
RUN sed -i 's/Components: main/Components: main contrib non-free/' /etc/apt/sources.list.d/debian.sources

# 2. Install Dependencies & Pre-accept License
# We combine the license acceptance and install into one block to prevent freezing
RUN apt-get update && \
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get install -y \
    pandoc \
    libssl-dev \
    libfontconfig1 \
    libgraphite2-3 \
    libharfbuzz0b \
    libicu-dev \
    wget \
    ttf-mscorefonts-installer \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Tectonic
RUN wget -qO- https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/

# 4. Refresh Font Cache (so Tectonic sees Arial)
RUN fc-cache -f -v

# 5. Copy Assets (Resume template)
COPY latex_assets ./latex_assets

# 6. Warm up Tectonic (The Robust Way)
# We copy the local file instead of using 'echo', preventing the "invalid character" error
COPY warmup.tex .
RUN tectonic warmup.tex && \
    rm warmup.tex warmup.pdf

# 7. Install Python Deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 8. Copy Code
COPY . .

# 9. Run
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
