# Cell Frequency Dashboard

Sistema local de extração, armazenamento e visualização de dados de frequência de membros de células do `app.celula.in`. 

O projeto automatiza a extração dos dados usando um script em Python (com requests HTTP autenticadas), armazena tudo em um banco de dados PostgreSQL com schema isolado por grupo (`group_id`), e fornece um dashboard interativo (FastAPI + HTML/JS com Chart.js) para análise de ausências e tendências.

## 🛠️ Arquitetura e Tecnologias

- **Extração:** Python (httpx, python-dotenv)
- **Banco de Dados:** PostgreSQL (schema multi-grupo idempotente com Upsert)
- **API & Servidor Web:** FastAPI + SQLAlchemy
- **Frontend:** HTML5, CSS3, Vanilla JS, Chart.js
- **Orquestração:** Docker & Docker Compose

## 🚀 Como Executar

### 1. Pré-requisitos
- Docker e Docker Compose instalados
- Python 3.10+ (caso queira rodar scripts localmente fora do container)
- Credenciais de acesso ao `app.celula.in`

### 2. Configuração
Clone o repositório e crie o arquivo de configuração:

```bash
cp .env.example .env
```

Edite o `.env` com os seus dados:
```env
CELULA_EMAIL=seu_email
CELULA_PASSWORD=sua_senha
CELULA_GROUP_ID=id_da_sua_celula
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres
# ou para o docker: postgresql://postgres:password@postgres:5432/postgres
```

### 3. Extraindo os Dados
A extração captura o token de acesso e faz fetch dos relatórios de presença, gerando arquivos NDJSON/CSV na pasta `artifacts/extract/`.

```bash
# Crie e ative o ambiente virtual (opcional)
python3 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt

# Execute a extração
python scripts/extract.py

# Verifique o schema gerado (opcional)
python scripts/verify_extract.py
```

### 4. Subindo o Sistema (DB + API + Dashboard)
Inicie os containers usando o Docker Compose:

```bash
docker-compose up --build -d
```
*Isso irá provisionar o banco PostgreSQL na porta 5432 e a API/Frontend na porta 8000.*

### 5. Populando o Banco de Dados
Com o banco rodando, importe os dados dos arquivos em `artifacts/extract/` para o PostgreSQL:

```bash
# Execute o script de migração para fazer o upsert no banco
python scripts/migrate_history.py
```

### 6. Acessando o Dashboard
Abra seu navegador e acesse:
👉 **[http://localhost:8000](http://localhost:8000)**

Na interface, insira o `Group ID` (o mesmo configurado no `.env`) para filtrar os resultados. O sistema exibe:
1. **Top Ausentes:** Membros com mais faltas nos últimos 2 meses.
2. **Presença vs Ausência:** Tendência por semana do mês (descobrir em qual semana ocorrem mais faltas).
3. **Top Presentes:** Pessoas com maior frequência em todo o histórico.

## 🗄️ Estrutura do Projeto

```text
.
├── backend/
│   ├── database.py       # Configuração do SQLAlchemy e conexão
│   ├── main.py           # App FastAPI, endpoints e montagem do frontend
│   └── models.py         # Schemas ORM (Group, Person, Event, Attendance)
├── frontend/
│   ├── app.js            # Lógica dos gráficos (Chart.js) e consumo da API
│   ├── index.html        # Estrutura do Dashboard
│   └── style.css         # Estilos (CSS)
├── scripts/
│   ├── extract.py        # Extração de dados da API do celula.in
│   ├── verify_extract.py # Validador de schema
│   ├── migrate_history.py# ETL (Lê os artefatos e faz Upsert no Postgres)
│   └── requirements.txt  # Dependências Python
├── artifacts/            # Output da extração de dados
├── docker-compose.yml    # Orquestração local
├── Dockerfile            # Imagem do Backend
└── .planning/            # Documentação interna (Roadmap, GSD, Specs)
```

## 🔒 Segurança e Isolamento
O sistema foi projetado nativamente para ser `multi-tenant` no banco de dados. Todas as tabelas e rotas da API exigem o `group_id`. Isso garante que você só vizualize e interaja com os dados referentes à sua célula, impossibilitando vazamento de informações inter-grupo.
