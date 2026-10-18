# Open Items

## Public observability endpoint

- Review/deploy the Prometheus collector and Caddy route; confirm all three host
  exporters report root filesystem metrics before replacing the portfolio samples.
- Add the metrics hostname to Cloudflare Tunnel separately, forwarding to Caddy
  with the matching Host header. Confirm WAF/cache policy preserves the response's
  `no-store` and `must-revalidate` directives; do not enable Always Online or an
  override cache TTL on the API route.
- Confirm the public HTTPS check allowlist and portfolio CORS origins before use.
- Connect the portfolio to the versioned JSON schema in
  [Public observability](docusaurus/docs/stack/public-observability.md).
