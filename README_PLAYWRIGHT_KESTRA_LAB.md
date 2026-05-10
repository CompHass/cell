# Extracao de frequencia (Célula.in) com Playwright API

Este repositorio esta em modo API-first.

Endpoints ja validados:
1. `POST /authenticate`
2. `GET /v1/groups/{groupId}?include=events`
3. `GET /v1/group-events/{eventId}?include=attendees,guests,group`

Nao e necessario fluxo de UI para extracao de frequencia no dia a dia.

## 1) Preparacao

1. Copie o arquivo de exemplo:
   ```bash
   cp .env.example .env
   ```
2. Preencha no minimo:
   - `CELULA_GROUP_ID` (obrigatorio)
   - `CELULA_TOKEN` (recomendado)
3. Se nao usar token, preencha:
   - `CELULA_EMAIL`
   - `CELULA_PASSWORD`
   - `CELULA_ACCOUNT`
4. Opcional:
   - `CELULA_MAX_EVENTS=0` para todos os eventos, ou um numero para limitar os mais recentes.

## 2) Execucao recomendada

```bash
docker compose run --rm playwright-lab npm run extract:attendance
```

Esse comando executa o modo API e remove o container ao final.

## 3) Saidas geradas

Arquivos em `artifacts/extract`:
1. `group.json`
2. `group_events_raw.ndjson`
3. `attendance_rows.ndjson`
4. `attendance.csv`
5. `attendance_summary_by_person.csv`
6. `event_summary.json`

## 4) Erros comuns

1. `Missing required env var: CELULA_GROUP_ID`
   - Defina `CELULA_GROUP_ID` no `.env`.
2. Erro de autenticacao
   - Revise `CELULA_TOKEN` ou as credenciais (`CELULA_EMAIL`, `CELULA_PASSWORD`, `CELULA_ACCOUNT`).

## 5) Modo legado (somente diagnostico)

`capture:network` continua disponivel, mas agora e opcional, apenas para investigar mudancas na aplicacao/API.

Comando legado:
```bash
docker compose up --build
```

Esse fluxo tenta navegar na UI e capturar trafego (`artifacts/network-summary.ndjson`), podendo falhar em redirecionamentos de login mesmo com extracao API funcionando.
