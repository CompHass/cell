# S01: Extração Python + Playwright — Research

**Date:** 2025-05-08
**Slice goal:** `python scripts/extract.py` roda, autentica no celula.in, e grava eventos e frequência em `artifacts/extract/` no mesmo formato que os scripts Node produziam.

## Summary

O trabalho de S01 é uma portagem direta de `scripts/extract-attendance.mjs` para Python — sem descoberta nova de API, sem risco de autenticação desconhecida. O fluxo de autenticação já está comprovado: `POST /authenticate` com `{username, password, account}` retorna `{"access_token": "...", "account": "..."}`. O token vai em `Authorization: Bearer` em todas as chamadas subsequentes.

O script Node usa `playwright.request` (sem browser) para todas as chamadas de API — nenhuma automação de DOM é necessária. A portagem para Python usa `playwright.async_api.async_playwright` com `APIRequestContext`, que é o equivalente direto. `seedBrowserAuth` do `capture-network.mjs` **não é necessário** em `extract.py` — ele só serve para abrir o browser e interceptar rede, o que `extract-attendance.mjs` já não faz.

O formato dos artefatos de saída está bem definido pelos dados históricos existentes em `artifacts/extract/` (2611 linhas em `attendance_rows.ndjson`, 115 eventos em `event_summary.json`). O script Python deve produzir exatamente o mesmo schema de campos.

## Recommendation

Escrever `scripts/extract.py` como portagem linha-a-linha do `extract-attendance.mjs` para Python, usando `playwright.async_api` (`APIRequestContext`) para as chamadas HTTP — sem browser headless. A autenticação é pura HTTP, a extração é pura HTTP; Playwright é usado apenas pelo seu `APIRequestContext` (equivale a `httpx` mas mantém a dependência única que será usada nos próximos slices se necessário).

> Alternativa: usar `httpx` ou `requests` diretamente sem Playwright. Isso é perfeitamente viável — o script Node usa `playwright.request`, não um browser real. O planner pode escolher `httpx` se preferir uma dependência mais leve; o resultado é idêntico.

## Implementation Landscape

### Key Files

- `scripts/extract-attendance.mjs` — script Node a ser portado; contém toda a lógica: autenticação, paginação de eventos, coleta de attendees/guests, geração dos NDJSON/CSV. Portagem é direta.
- `scripts/capture-network.mjs` — script de captura genérica; **não** é portado em S01; serve de referência para o padrão `seedBrowserAuth` que pode ser útil em slices futuros se o login via browser for necessário.
- `artifacts/extract/attendance_rows.ndjson` — 2611 linhas, formato: `{event_id, event_date, event_name, person_id, person_name, status, group_id}`. O script Python deve produzir o mesmo schema.
- `artifacts/extract/event_summary.json` — array de 115 objetos, formato: `{event_id, event_date, event_name, attendees_count, absentees_inferred_count, people_total, status}`.
- `artifacts/extract/group.json` — resposta completa de `GET /v1/groups/{group_id}?include=events`; IDs de eventos em `data.relationships.events.data[].id`.
- `.env.example` — todas as variáveis necessárias já mapeadas: `CELULA_EMAIL`, `CELULA_PASSWORD`, `CELULA_ACCOUNT`, `CELULA_GROUP_ID`, `CELULA_API_BASE`, `CELULA_MAX_EVENTS`.

### API Endpoints (já confirmados pelos artifacts)

1. `POST /authenticate` — body: `{username, password, account}` — retorna `{access_token, account}` — **sem JSON:API wrapper**
2. `GET /v1/groups/{group_id}?include=events` — retorna JSON:API com `data.relationships.events.data[].id`
3. `GET /v1/group-events/{event_id}?include=attendees,guests,group` — retorna JSON:API com `included[]` de `type:"people"` e `data.relationships.{attendees,guests}.data[].id`

### Output Files (S01 produces)

```
artifacts/extract/
  attendance_rows.ndjson          # uma linha JSON por (evento × pessoa)
  event_summary.json              # array com resumo por evento
  group_events_raw.ndjson         # resposta bruta de cada evento (uma linha = um evento)
  attendance.csv                  # attendance_rows em CSV
  attendance_summary_by_person.csv # ranking de presença por pessoa
  group.json                      # resposta bruta de GET /v1/groups/{id}
```

### Build Order

1. **Função `authenticate()`** — `POST /authenticate`, extrai `access_token`. Testar isoladamente com `.env` real antes de seguir.
2. **Função `fetch_group_events()`** — `GET /v1/groups/{id}?include=events`, extrai lista de IDs de eventos.
3. **Loop de extração** — para cada event_id: `GET /v1/group-events/{id}?include=attendees,guests,group`, monta `attendance_rows` e `event_summaries`.
4. **Geração de artefatos** — escreve NDJSON/JSON/CSV idênticos ao formato existente.
5. **Verificação de paridade** — comparar output do script Python com os `artifacts/extract/` existentes (mesmos event_ids, mesmos person_ids, mesmo campo `group_id`).

O passo 1 unbloqueia tudo; se autenticação mudar desde os scripts Node (token expirado ou fluxo diferente para conta supervisionada), isso é detectado imediatamente.

### Verification Approach

```bash
# Roda o script (requer .env com credenciais válidas)
python scripts/extract.py

# Verifica que attendance_rows.ndjson tem linhas e schema correto
python3 -c "
import json
with open('artifacts/extract/attendance_rows.ndjson') as f:
    rows = [json.loads(l) for l in f if l.strip()]
print(f'{len(rows)} rows')
required = {'event_id','event_date','event_name','person_id','person_name','status','group_id'}
assert all(required <= set(r.keys()) for r in rows), 'schema mismatch'
print('schema OK')
"

# Verifica event_summary.json
python3 -c "
import json
with open('artifacts/extract/event_summary.json') as f:
    ev = json.load(f)
print(f'{len(ev)} events')
assert all('event_id' in e and 'attendees_count' in e for e in ev), 'schema mismatch'
print('schema OK')
"
```

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| HTTP com headers persistentes e JSON:API | `playwright.async_api.APIRequestContext` ou `httpx.AsyncClient` | Evita reimplementar session/headers — ambos suportam `extra_http_headers` e `base_url` |
| Leitura de `.env` | `python-dotenv` (`dotenv.load_dotenv()`) | Uma linha; evita reimplementar o parser de `.env` do script Node |

## Constraints

- Python 3.11+ (conforme decisão D001)
- `playwright` Python é a dependência de browser — já decidida (D002); para S01 especificamente, `playwright.async_api` cobre o caso sem precisar de browser headless (só `APIRequestContext`)
- Artefatos de saída em `artifacts/extract/` devem ser **exatamente** o mesmo schema dos arquivos existentes — S02 depende desse formato para a migração histórica
- `group_id` **deve** vir de `CELULA_GROUP_ID` no `.env` e deve ser gravado em cada linha de `attendance_rows.ndjson`

## Common Pitfalls

- **Token extraction path** — a resposta de `/authenticate` retorna `{"access_token": "...", "account": "..."}` diretamente (não aninhado em `data.attributes`). O script Node cobre múltiplos caminhos (`payload.access_token || payload.token || payload.data.attributes.token || payload.data.token`). Manter todos os fallbacks.
- **`absentees_inferred_count` vs ausências reais** — a API não retorna "ausentes" diretamente. Ausentes = pessoas em `guests` que não estão em `attendees`. O script Node faz esse cálculo; o Python deve replicar exatamente.
- **Datas em UTC** — `event_date` vem como ISO 8601 com `Z` (ex: `"2022-01-27T03:00:00.000Z"`). Gravar exatamente como recebido da API; não converter timezone (S02 e S03 farão isso na query).
- **Encoding** — `person_name` pode ter caracteres Unicode (ex: `"Reunião de célula"`). Garantir `ensure_ascii=False` no `json.dumps`.

## Open Risks

- **Conta supervisionada vs. conta própria** — o `CELULA_GROUP_ID` configurado (`61f2d4aa578b3700190c5bb8`) é o grupo do usuário logado. Se Eduardo tentar extrair um grupo supervisionado (onde ele é supervisor, não líder), o endpoint `/v1/groups/{id}?include=events` pode retornar 403 ou lista de eventos vazia. Isso é um risco listado no M001-CONTEXT.md e será descoberto na execução de S01.
- **Token expirado** — o token capturado em `artifacts/network/0002_200_POST__authenticate.json` já está expirado (exp no JWT). O script Python gera um novo token a cada execução, então isso não é problema — mas valida que as credenciais no `.env` estão atuais.
