# Cell Frequency Dashboard

## What This Is

Sistema local de extração, armazenamento e visualização de dados de frequência de membros de células. Extrai dados do app.celula.in via Playwright Python autenticado, grava em Postgres local, e serve um dashboard web com gráficos dinâmicos via FastAPI — tudo rodando via Docker Compose sem dependências externas.

## Core Value

Visualizar quem está faltando e qual semana do mês tem mais ausências, com dados isolados por grupo, sem depender do celula.in para análise.

## Project Shape

- **Complexity:** complex
- **Why:** Envolve autenticação SPA, pipeline de extração, schema relacional multi-grupo, API e dashboard — múltiplas camadas que precisam funcionar juntas.

## Current State

Scripts de exploração em Node.js/Playwright existem (`scripts/capture-network.mjs`, `scripts/extract-attendance.mjs`) e já produziram dados históricos reais em `artifacts/extract/`. A API do celula.in usa JSON:API format com autenticação Bearer token via `/authenticate`. Dados históricos de ~115 eventos e ~30 pessoas estão disponíveis para migração.

## Architecture / Key Patterns

- **Extração:** Python + Playwright (substitui scripts Node existentes)
- **Storage:** Postgres local (Docker), schema multi-grupo com `group_id` em todas as tabelas
- **Backend/API:** FastAPI + SQLAlchemy, serve também o frontend estático
- **Frontend:** HTML/CSS/JS com Chart.js, layout gerado com Open Design
- **Orquestração:** Docker Compose — `postgres` + `api` (FastAPI unifica backend + frontend)
- **Convenções:** camelCase nos scripts Python, snake_case no schema SQL, `group_id` obrigatório em todas as queries

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [ ] M001: Cell Frequency Dashboard — Extração Python + Postgres + FastAPI + Dashboard com 3 gráficos, tudo via Docker Compose
