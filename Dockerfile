# Use a slim base image
FROM python:3.10-slim

# Optional: Use ARGs for flexible build-time config (e.g., ENV)
ARG ENVIRONMENT=production

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code into the image
COPY . .

# Optional: Set environment variable inside the container
ENV ENVIRONMENT=$ENVIRONMENT

# Define the default command to run your app
CMD ["python3", "-m", "polybot.app"]

