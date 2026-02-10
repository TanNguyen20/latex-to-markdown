FROM python:3.11-slim

# 1. Install System Dependencies
# Added: 'software-properties-common' and 'contrib' repo to get Microsoft fonts
# Added: 'ttf-mscorefonts-installer' setup
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    # Enable contrib and non-free repositories for MS fonts
    apt-add-repository contrib && \
    apt-add-repository non-free && \
    apt-get update

# 2. Pre-accept the Microsoft Font License (REQUIRED for silent install)
RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

# 3. Install Dependencies & Fonts
RUN apt-get install -y \
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

# 4. Install Tectonic
RUN wget -qO- https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/

# 5. Refresh Font Cache
# This makes sure Tectonic "sees" the new Arial font
RUN fc-cache -f -v

# 6. Copy Assets (Resume template, etc)
# Make sure your 'latex_assets' folder exists locally!
COPY latex_assets ./latex_assets

# 7. Warm up Tectonic (Optional but recommended)
RUN echo "\\documentclass{article}\\begin{document}Warmup\\end{document}" > warmup.tex && \
    tectonic warmup.tex && \
    rm warmup.tex warmup.pdf

# 8. Install Python Deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 9. Copy Code
COPY . .

# 10. Run
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
