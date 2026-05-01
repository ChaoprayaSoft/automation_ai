# Use the official Microsoft Playwright image with Python pre-installed
# This image already contains all necessary system libraries for Chromium
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements and install
# Note: playwright is already in the base image, but we install your specific versions
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port your Flask app runs on
EXPOSE 5000

# Start the application using Gunicorn
# Using --chdir server because your app.py is inside the /server folder
CMD ["gunicorn", "--chdir", "server", "--bind", "0.0.0.0:5000", "app:app"]
