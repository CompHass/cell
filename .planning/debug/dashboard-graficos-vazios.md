---
status: resolved
trigger: "nao consigo ver os dados na tela ainda — graficos vazios rodando via Podman Compose"
created: 2026-05-08T15:10:00Z
updated: 2026-05-08T15:10:00Z
---

## Symptoms
- expected: dashboard com 3 gráficos renderizados ao abrir localhost:8000
- actual: gráficos renderizam (canvas presente) mas sem dados
- errors: nenhum erro visível no console do browser
- runtime: Podman/Docker Compose
- timeline: localmente os endpoints retornam dados corretamente

## Current Focus
hypothesis: "banco Postgres no container está vazio — migração não executou ou falhou silenciosamente no entrypoint.sh"
next_action: "gather initial evidence"
