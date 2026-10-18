FROM node:22-slim

# OpenClaw AI gateway. One Claude provider, anthropic: the Claude API with an
# API key read from the ANTHROPIC_API_KEY environment variable at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g openclaw

# Run as node:22-slim's built-in uid-1000 `node` user rather than root.
ENV OPENCLAW_STATE_DIR=/home/node/.openclaw
ENV HOME=/home/node
WORKDIR /home/node

# Ship the sanitized, claude-only config (no secrets) into the image.
COPY --chown=node:node openclaw.json /home/node/.openclaw/openclaw.json
RUN chown -R node:node /home/node
USER node

EXPOSE 18789
# Bind to the LAN so other hosts/Caddy can reach it; auth via a token from env.
CMD ["sh", "-c", "openclaw gateway --bind lan --auth token --port 18789"]
