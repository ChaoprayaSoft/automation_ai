# Use the exact version matching your requirements
FROM mcr.microsoft.com/playwright/python:v1.59.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Start application
CMD ["gunicorn", "--chdir", "server", "--bind", "0.0.0.0:5000", "app:app"]
