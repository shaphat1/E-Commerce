# Build from the REPOSITORY ROOT so the legal documents can be copied in:
#   docker build -f backend/Dockerfile -t maumart-backend .
# (docker-compose.yml already does this.)
#
# Status: the build and `docker compose up` are exercised by the CI workflow's `docker` job;
# they could not be run in the environment that produced this file (no Docker daemon).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg2-binary and bcrypt ship wheels: no compiler or libpq-dev needed in the image.
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
# The storefront footer serves these (main.py looks in ./legal inside the container).
COPY TERMS_OF_SERVICE.md PRIVACY_POLICY.md REFUND_POLICY.md VENDOR_AGREEMENT.md ./legal/

# Run as a non-root user
RUN useradd --create-home --shell /usr/sbin/nologin maumart && chown -R maumart:maumart /app
USER maumart

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)" || exit 1

# Behind a reverse proxy, set FORWARDED_ALLOW_IPS to the proxy's address so the real client IP
# (not the proxy's) is used for rate limiting. WEB_CONCURRENCY sets the number of workers.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
