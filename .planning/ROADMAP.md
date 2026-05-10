# Roadmap

## M001: Cell Frequency Dashboard

- [ ] **Phase 01: s01** — S01
    **Plans:** 2 plans
    - [ ] 01-01-PLAN.md — Implementar extração de frequência (extract.py)
    - [ ] 01-02-PLAN.md — Validar schema de saída
- [ ] **Phase 02: schema-postgres-migra-o-hist-rica** — Schema Postgres + migração histórica
    **Plans:** 2 plans
    - [ ] 02-01-PLAN.md — Define SQLAlchemy models and DB connection
    - [ ] 02-02-PLAN.md — Build historical migration script
- [ ] **Phase 03: api-fastapi-com-endpoints-de-frequ-ncia** — API FastAPI com endpoints de frequência
    **Plans:** 2 plans
    - [ ] 03-01-PLAN.md — Initialize FastAPI and group endpoints
    - [ ] 03-02-PLAN.md — Implement analytical endpoints
- [ ] **Phase 04: dashboard-html-com-3-gr-ficos** — Dashboard HTML com 3 gráficos
    **Plans:** 2 plans
    - [ ] 04-01-PLAN.md — Setup dashboard HTML skeleton and serve via FastAPI
    - [ ] 04-02-PLAN.md — Implement frontend logic to fetch API data and render charts
- [ ] **Phase 05: docker-compose-completo-pipeline-end-to-end** — Docker Compose completo + pipeline end-to-end
- [ ] **Phase 06: dashboard-filtros-pessoa-data-grupo** — Dashboard com filtros: pessoa, data (de/até) e grupo
    **Goal:** Adicionar filtros interativos ao dashboard — filtrar por pessoa, por intervalo de datas e por grupo
    **Depends on:** Phase 04, Phase 05
    **Requirements:** [R007, R004, R005]
    **Plans:** 3 plans
    - [ ] 06-01-PLAN.md — Add date/person filter params to FastAPI endpoints
    - [ ] 06-02-PLAN.md — Add filter controls to dashboard HTML/CSS
    - [ ] 06-03-PLAN.md — Wire filter controls to API calls in app.js
- [ ] **Phase 07: pipeline-build-push-imagens-front-backend** — Pipeline de build e push das imagens do front e backend
    **Goal:** Build e push de imagens Docker separadas (frontend + backend) para harbor.hasslab.pro via GitHub Actions no push para main
    **Depends on:**
    **Plans:** 2 plans
    - [ ] 07-01-PLAN.md — Create Dockerfile.backend and Dockerfile.frontend
    - [ ] 07-02-PLAN.md — GitHub Actions workflow: build and push both images to Harbor
