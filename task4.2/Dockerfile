# ---- Task 4.2: Flask app container ----
# Slim base image: much smaller than the full python image.
FROM python:3.13-slim

# Do not write .pyc files; flush logs straight to `docker logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first so the pip layer is cached
# and only rebuilt when dependencies change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (tests/venv excluded via .dockerignore).
COPY app.py .

# Run as a non-root user for security.
RUN useradd --create-home appuser
USER appuser

# Document the port the app listens on inside the container.
EXPOSE 5000

# Production WSGI server, bound to 0.0.0.0 so it is reachable from the host.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:create_app()"]