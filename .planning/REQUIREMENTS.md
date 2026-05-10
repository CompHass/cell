# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R001 — Extração autenticada de frequência
- Class: core-capability
- Status: active
- Description: Script Python com Playwright autentica no celula.in via token Bearer e extrai eventos e registros de frequência por grupo
- Why it matters: É a fonte primária de dados — sem extração funcionando, nada mais funciona
- Source: user
- Primary owning slice: M001/S01
- Supporting slices: M001/S05
- Validation: mapped
- Notes: A API usa JSON:API format; autenticação via POST /authenticate retorna Bearer token; seedBrowserAuth injeta token no localStorage do SPA

### R002 — Storage Postgres multi-grupo
- Class: core-capability
- Status: active
- Description: Schema Postgres com tabelas `groups`, `events`, `attendance` — todas com `group_id` como coluna obrigatória. Upsert idempotente para re-extrações.
- Why it matters: Permite queries relacionais, isolamento por grupo, e histórico versionável
- Source: user
- Primary owning slice: M001/S02
- Supporting slices: M001/S05
- Validation: mapped
- Notes: group_id vem do env var CELULA_GROUP_ID; upsert via ON CONFLICT para idempotência

### R003 — API FastAPI para dados de frequência
- Class: core-capability
- Status: active
- Description: Endpoints REST para consulta de frequência filtrados por group_id, período e pessoa
- Why it matters: Desacopla o dashboard do storage e permite futuras integrações
- Source: user
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: mapped
- Notes: FastAPI serve também o frontend estático; documentação Swagger automática em /docs

### R004 — Dashboard com 3 gráficos prioritários
- Class: primary-user-loop
- Status: active
- Description: Interface web com (1) top ausentes últimos 2 meses, (2) presença vs ausência por semana do mês, (3) top presentes histórico
- Why it matters: É o motivo principal do sistema — visualizar padrões de frequência sem depender do celula.in
- Source: user
- Primary owning slice: M001/S04
- Supporting slices: M001/S03
- Validation: mapped
- Notes: Layout gerado com Open Design; gráficos via Chart.js; filtro por grupo na UI

### R005 — Filtro por grupo (isolamento de dados)
- Class: compliance/security
- Status: active
- Description: Todas as queries e views filtram por group_id — dados de um grupo nunca aparecem em views de outro
- Why it matters: Eduardo é supervisor de múltiplos grupos; misturar dados comprometeria a análise
- Source: user
- Primary owning slice: M001/S03
- Supporting slices: M001/S02, M001/S04
- Validation: mapped
- Notes: group_id é parâmetro obrigatório em todos os endpoints da API

### R006 — Importação dos dados históricos existentes
- Class: continuity
- Status: active
- Description: Script de migração lê os arquivos `artifacts/extract/attendance_rows.ndjson` e `event_summary.json` e popula o Postgres
- Why it matters: Existe histórico real desde 2022 — perder esses dados ao migrar seria um retrocesso
- Source: inferred
- Primary owning slice: M001/S02
- Supporting slices: none
- Validation: mapped
- Notes: Arquivos em artifacts/extract/ já existem com dados reais de ~115 eventos

### R007 — Stack 100% local via Docker Compose
- Class: constraint
- Status: active
- Description: `docker compose up` sobe o sistema completo — Postgres + API + dashboard — sem dependências externas ou serviços cloud
- Why it matters: Dados de membros da comunidade ficam sob controle local; sem custos de serviço
- Source: user
- Primary owning slice: M001/S05
- Supporting slices: M001/S01, M001/S02, M001/S03
- Validation: mapped
- Notes: Node.js removido do runtime; único runtime é Python

## Deferred

### R008 — Agendamento automático de extração
- Class: operability
- Status: deferred
- Description: Cron job ou scheduler que roda a extração automaticamente em intervalo configurável
- Why it matters: Eliminaria a necessidade de rodar o script manualmente
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferido — extração manual é suficiente por ora

### R009 — Deploy externo / multi-usuário
- Class: operability
- Status: deferred
- Description: Acesso ao dashboard por outras pessoas da equipe via URL pública
- Why it matters: Permitiria que líderes de célula visualizem os próprios dados
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferido — uso local é suficiente por ora

## Out of Scope

### R010 — Escrita de dados de volta ao celula.in
- Class: anti-feature
- Status: out-of-scope
- Description: O sistema é read-only — não cria, edita ou deleta dados no celula.in
- Why it matters: Previne corrupção acidental de dados na fonte
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Explicitamente excluído na discussão

### R011 — Firecrawl / serviços cloud de scraping
- Class: anti-feature
- Status: out-of-scope
- Description: Nenhuma dependência de serviços cloud de scraping (Firecrawl, etc.)
- Why it matters: Mantém a stack 100% local e sem custos externos
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Decisão explícita na discussão — Playwright local é suficiente

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | core-capability | active | M001/S01 | M001/S05 | mapped |
| R002 | core-capability | active | M001/S02 | M001/S05 | mapped |
| R003 | core-capability | active | M001/S03 | none | mapped |
| R004 | primary-user-loop | active | M001/S04 | M001/S03 | mapped |
| R005 | compliance/security | active | M001/S03 | M001/S02, M001/S04 | mapped |
| R006 | continuity | active | M001/S02 | none | mapped |
| R007 | constraint | active | M001/S05 | M001/S01, M001/S02, M001/S03 | mapped |
| R008 | operability | deferred | none | none | unmapped |
| R009 | operability | deferred | none | none | unmapped |
| R010 | anti-feature | out-of-scope | none | none | n/a |
| R011 | anti-feature | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 7
- Mapped to slices: 7
- Validated: 0
- Unmapped active requirements: 0
