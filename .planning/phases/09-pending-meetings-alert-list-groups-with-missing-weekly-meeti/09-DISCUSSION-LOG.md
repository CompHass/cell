# Phase 9: Pending Meetings Alert - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-12
**Phase:** 09-pending-meetings-alert-list-groups-with-missing-weekly-meeti
**Areas discussed:** Definição de semana, Onde aparece no dashboard

---

## Definição de semana

| Option | Description | Selected |
|--------|-------------|----------|
| Domingo a sábado | Semana vai de domingo a sábado | |
| Segunda a domingo | Semana vai de segunda a domingo | ✓ |

**User's choice:** Segunda a domingo

---

| Option | Description | Selected |
|--------|-------------|----------|
| A partir de domingo | Alerta ativa a partir de domingo, checa semana anterior segunda–domingo | ✓ |
| A partir de segunda | Alerta ativa a partir de segunda | |
| Qualquer dia | Qualquer dia da nova semana já dispara o alerta | |

**User's choice:** A partir de domingo

---

| Option | Description | Selected |
|--------|-------------|----------|
| Qualquer evento na semana | Qualquer evento registrado na semana conta | ✓ |
| Evento com pelo menos 1 presente | Evento deve ter status=present para alguém | |
| Usar lógica valid_event existente | Reusa _get_valid_event_ids do backend | |

**User's choice:** Qualquer evento na semana
**Notes:** Não exige presença — apenas que o evento tenha sido registrado.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Apenas última semana | Mostra só a semana anterior imediata | |
| Todas as semanas pendentes | Acumula todas as semanas sem reunião desde o início | ✓ |
| N semanas configurável | Janela configurável | |

**User's choice:** Todas as semanas pendentes

---

| Option | Description | Selected |
|--------|-------------|----------|
| Desde o primeiro evento | Conta desde o primeiro evento registrado do grupo | ✓ |
| Janela de tempo configurável | Apenas nos últimos N meses | |
| Data de corte fixa | Desde data fixa (ex: início do ano) | |

**User's choice:** Desde o primeiro evento

---

## Onde aparece no dashboard

| Option | Description | Selected |
|--------|-------------|----------|
| Seção fixa no topo | Bloco antes dos gráficos | |
| Seção no final | Após os gráficos | |
| Banner flutuante | Banner/alerta sticky | |
| Far right metric card | Card adicional junto aos metric cards, totalmente à direita | ✓ |

**User's choice:** Card junto aos metric cards, à direita (freeform)
**Notes:** Screenshot do dashboard mostrou a faixa: Participantes / Presença Média / Em Risco / Qualificados 3×. O novo card vai na direita dessa faixa.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Sempre visível | Mostra mesmo quando todos em dia | |
| Só quando há pendentes | Card some quando todos em dia | ✓ |
| Colapsável | Cabeçalho sempre visível, lista expansível | |

**User's choice:** Só quando há pendentes

---

| Option | Description | Selected |
|--------|-------------|----------|
| Mesmo estilo dos outros cards | Label pequeno + número grande | ✓ |
| Card expandido com nomes | Lista nomes dentro do card | |
| Badge + detalhe ao clicar | Contador + click abre detalhe | |

**User's choice:** Mesmo estilo dos outros cards (label + número)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Click expande detalhe | Click no card abre lista de grupos + semanas pendentes | ✓ |
| Só o número | Sem drill-down | |
| Lista automática abaixo | Lista detalhada sempre visível abaixo dos cards | |

**User's choice:** Click expande detalhe

---

## the agent's Discretion

- Label text do card (ex: "REUNIÕES PENDENTES")
- Se o detalhe é inline expansível ou modal
- Cor do número (sugerido: vermelho, como "Em Risco")

## Deferred Ideas

Nenhuma ideia de escopo extra levantada durante a discussão.
