FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn httpx

# Copy mock service code
COPY . .

# Expose port
EXPOSE 8000

# Run mock services
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]