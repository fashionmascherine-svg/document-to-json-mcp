# Dockerfile for Apify Actor
# Document-to-JSON Converter
FROM apify/actor-python:3.11

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ita \
    tesseract-ocr-spa \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-por \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Apify SDK
RUN pip install --no-cache-dir apify

# Copy the rest of the code
COPY . ./

# Set the entrypoint
CMD ["python", "-m", "src.apify_entrypoint"]
