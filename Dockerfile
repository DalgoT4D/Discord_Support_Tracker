FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install uv from PyPI; staging can't pull ghcr.io images during builds
RUN pip install --no-cache-dir uv

# Install dependencies first so code changes don't re-download them
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY discord_support_bot.py ./

# SIGINT triggers the bot's KeyboardInterrupt cleanup path (same as pm2)
STOPSIGNAL SIGINT

CMD [".venv/bin/python", "discord_support_bot.py"]
