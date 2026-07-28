# AGENTS.md — SPOTBOT PRO WORKSPACE RULES & DEPLOYMENT PROTOCOLS

## ☁️ RAILWAY CLOUD DEPLOYMENT PROTOCOL (24/7 PRODUCTION)
- **Automatic Deployment Trigger**: Every single code change, fix, feature, or refactoring MUST be committed (`git commit`) and pushed (`git push`) to the GitHub repository (`master` branch) so Railway automatically builds and deploys the update.
- **Hybrid Database System**:
  - Local Execution: Uses SQLite (`sqlite:///spotbot.db`).
  - Railway Cloud Execution: Uses PostgreSQL (`postgresql://...` or `postgres://...`) via the automatically injected `DATABASE_URL` environment variable.
  - All database queries and schema migrations in `services/database.py` MUST maintain 100% hybrid compatibility between SQLite and PostgreSQL.
- **Network & Host Binding**:
  - The Web Dashboard (`ui/dashboard.py`) MUST always listen on `host='0.0.0.0'` and dynamic port `PORT` (default 8080) for cloud compatibility.
