# Working on the datathon template

Start with the [README](README.md) for local setup and the [architecture guide](ARCHITECTURE.md) to trace a feature across the two apps.

- For dashboard UI, authentication, and portfolio storage in Aurora PostgreSQL, follow the [frontend instructions](frontend-dashboard/AGENTS.md).
- For stock prices, price history, news, and sector rankings, follow the [backend instructions](backend-server/AGENTS.md).
- When a change spans both apps, read both guides. Trace the existing request from the dashboard to the FastAPI route before changing it. If you change a response field, its units, or how missing data is represented, update the callers that depend on it.

## Keep the docs current

Update [ARCHITECTURE.md](ARCHITECTURE.md) in the same change whenever the code changes how the system works. Examples include moving data to a different service, changing how portfolio access is enforced, or switching article providers. Update the affected explanation and the diagram if its arrows or labels have changed. A styling change or internal refactor that leaves the guide accurate needs no documentation edit.

If setup changes, update the affected app's README and its `.env.example` for any new configuration. Keep credentials in local environment files.
