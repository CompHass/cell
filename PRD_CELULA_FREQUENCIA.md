# PRD - Extração e Visualização de Frequência (Célula.in)

## 1. Contexto

Atualmente os dados de frequência de pessoas estão no `https://app.celula.in/` e acessíveis via navegador autenticado.  
Chamadas diretas via `curl` falham por depender de sessão autenticada (cookies/token de navegador), o que indica fluxo protegido por autenticação web (possivelmente app SPA/server-side híbrido).

Objetivo: criar uma solução sob controle próprio para extrair, armazenar e visualizar esses dados com mais flexibilidade.

## 2. Objetivos de Produto

- Acessar dados de frequência no Célula.in com autenticação válida.
- Armazenar dados em estrutura própria e versionável.
- Criar camada de visualização com gráficos dinâmicos.
- Permitir filtros por pessoas, período, grupo e status.
- Habilitar criação rápida de novos gráficos e relatórios customizados.

## 3. Não Objetivos (Inicialmente)

- Alterar dados no Célula.in (somente leitura nesta fase).
- Substituir completamente o sistema original.
- Criar app mobile nativo nesta primeira etapa.

## 4. Hipótese Técnica Principal

### 4.1 Playwright é uma boa ideia?

Sim, para este caso é uma abordagem forte e pragmática.

Motivos:
- Resolve autenticação real de navegador (cookies/session/token dinâmico).
- Permite capturar chamadas de rede após login (`page.on('response')`, `context.storageState()`).
- É estável para automação recorrente com fluxo de login controlado.
- Evita engenharia reversa frágil de headers/tokens sem contexto de browser.

Limites:
- Pode quebrar se fluxo de login/UI mudar.
- Exige cuidado com captcha/MFA (se houver).
- Necessita gestão segura de credenciais e sessão.

Decisão:
- Usar Playwright para descoberta e ingestão inicial.
- Tentar migrar para requisição HTTP direta autenticada somente se endpoint e headers ficarem estáveis depois da descoberta.

## 5. Requisitos Funcionais

1. Fazer login no Célula.in com credenciais fornecidas em ambiente seguro.
2. Navegar para página de frequência alvo.
3. Identificar e capturar request/response que retorna os dados de frequência.
4. Normalizar dados para um schema próprio.
5. Persistir dados historicamente.
6. Expor dados para ferramenta externa de visualização (BI/dashboard).
7. Permitir filtros dinâmicos por período, pessoa e grupo.
8. Gerar visualizações dinâmicas (linha, barra, heatmap, tabela detalhada).

## 6. Requisitos Não Funcionais

- Segurança: credenciais em secret manager/env, nunca hardcoded.
- Confiabilidade: retentativa automática e logging de falhas.
- Observabilidade: logs de execução e trilha de ingestão por timestamp.
- Performance: ingestão incremental (evitar full load desnecessário).
- Manutenibilidade: separação entre captura, transformação e visualização.

## 7. Arquitetura Proposta (v1)

### 7.1 Coletor

- Tecnologia: Node.js + Playwright.
- Funções:
  - Login automatizado.
  - Captura de request/response da frequência.
  - Export bruto (`raw json`) para auditoria.
  - Transformação para schema canônico.

### 7.2 Armazenamento

Opção recomendada para início:
- PostgreSQL (tabelas normalizadas + snapshots).

Alternativa rápida:
- Arquivos `JSON/Parquet` versionados por data + posterior carga em banco.

### 7.3 Camada Semântica

- Views/tabelas derivadas com métricas:
  - presença total
  - taxa de frequência por pessoa
  - tendência por período
  - faltas consecutivas

### 7.4 Visualização

Opções:
- Metabase/Superset/Power BI/Looker Studio.
- Dash custom (React + ECharts/Recharts/Plotly) se quiser máxima liberdade.

## 8. Modelo de Dados Inicial

### 8.1 `people`
- `person_id` (pk)
- `name`
- `group_name`
- `active`
- `created_at`
- `updated_at`

### 8.2 `attendance_events`
- `event_id` (pk)
- `person_id` (fk)
- `event_date`
- `status` (present, absent, justified, etc.)
- `source_record_hash` (deduplicação)
- `ingested_at`

### 8.3 `ingestion_runs`
- `run_id` (pk)
- `started_at`
- `finished_at`
- `status`
- `records_raw`
- `records_valid`
- `error_message`

## 9. Fluxo de Execução

1. Job inicia (manual ou agendado).
2. Playwright abre browser/context autenticado.
3. Script faz login (ou reutiliza `storageState` válido).
4. Navega para tela de frequência.
5. Intercepta resposta de endpoint relevante.
6. Salva payload bruto.
7. Normaliza e upsert no banco.
8. Atualiza tabelas derivadas/materializadas.
9. Dispara atualização do dashboard.

## 10. Estratégia de Segurança

- Guardar credenciais em variáveis de ambiente ou vault.
- Criptografar artefatos sensíveis de sessão (`storageState`).
- Rotacionar sessão periodicamente.
- Sanitizar logs (sem senha/token).
- Restringir acesso ao banco e dashboards por papel.

## 11. Riscos e Mitigações

1. Mudança de frontend/endpoints no Célula.in  
Mitigação: testes de contrato no payload e alertas de quebra.

2. Sessão expirada/captcha/MFA  
Mitigação: rotina de reautenticação + fallback manual.

3. Dados incompletos por paginação/filtros invisíveis  
Mitigação: validações de contagem e reconciliação por período.

4. Bloqueio por automação  
Mitigação: intervalos humanos, respeito a limites e execução controlada.

## 12. Critérios de Aceite (MVP)

1. Coletor captura dados de frequência com sucesso em ambiente real.
2. Pipeline grava dados no banco com histórico.
3. Dashboard apresenta pelo menos:
   - frequência por pessoa (período selecionável)
   - ranking de presença
   - evolução temporal do grupo
4. Filtros funcionam sem recarregar página inteira.
5. Job agendado executa diariamente com logs e status.

## 13. Roadmap Sugerido

### Fase 1 - Descoberta Técnica (1-3 dias)
- Implementar script Playwright de login.
- Mapear requests relevantes e schema do payload.
- Provar extração ponta a ponta com dump local.

### Fase 2 - Ingestão e Persistência (2-5 dias)
- Definir schema do banco.
- Implementar normalização e upsert.
- Criar execução agendada e monitorada.

### Fase 3 - Visualização (2-5 dias)
- Conectar BI ao banco.
- Criar dashboards dinâmicos com filtros principais.
- Validar consistência com dados do Célula.in.

### Fase 4 - Escala e Governança
- Testes automatizados do pipeline.
- Alertas e observabilidade.
- Novos gráficos customizados e camada de métricas.

## 14. Backlog Técnico Inicial

- Script Playwright:
  - login
  - captura de responses
  - persistência de sessão
- Parser de payload e mapeamento para schema interno
- Migrations do banco
- Job scheduler (cron/GitHub Actions/worker)
- Dashboard base + filtros
- Monitoramento e alertas de falha

## 15. Próximos Passos Imediatos

1. Validar este PRD.
2. Executar POC de captura com Playwright para identificar endpoint exato.
3. Congelar schema v1 e iniciar pipeline de ingestão.

