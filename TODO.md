## TODO:

- Phase 5: Analytics API (Days 10–11)
GET /api/v1/links/{slug}/analytics returns clicks over time, top referrers, and device breakdown. This is mostly DB queries — practice writing clean SQL via SQLAlchemy. Write tests against real data fixtures.

- Phase 6: Observability (Days 12–13)
Add Prometheus metrics (auto-instrumented + custom: cache hit/miss ratio as a Counter). Set up the Grafana dashboard. Add structlog with a middleware that injects a request_id correlation ID into every log line. Deploy to Fly.io with a fly.toml.

- Phase 7: Polish (Days 14–15)
Write the README with an architecture diagram, local setup instructions, and an ADR explaining your caching and analytics buffering decisions. Clean up git history with meaningful conventional commits. Add a CHANGELOG.md.

- Phase 8: Front-end and Cloud??
- integrate with AWS
- create simple frontend