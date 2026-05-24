# Production Deployment Notes

1. Set `ENVIRONMENT=production`, `ENABLE_DATABASE=true`, and a strong `AUTH_SECRET_KEY`.
2. Use managed PostgreSQL and run `alembic upgrade head` before starting the API.
3. Set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` for hosted LLM summaries.
4. Set `RAG_BACKEND=postgres` and seed `knowledge_documents` for database-backed retrieval.
5. Put the API behind TLS, configure centralized logs, and rotate `AUTH_USERS` into a real identity provider before regulated use.
