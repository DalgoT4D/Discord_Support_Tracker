FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first so code changes don't re-download them
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY discord_support_bot.py ./

# SIGINT triggers the bot's KeyboardInterrupt cleanup path (same as pm2)
STOPSIGNAL SIGINT

CMD [".venv/bin/python", "discord_support_bot.py"]
