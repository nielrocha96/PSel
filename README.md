
# PSel — Aplicação de Análise Inteligente de Planilhas (FastAPI + Frontend)

Este projeto implementa um sistema local (containerizado via Docker Compose) que permite:

1. Fazer upload de um arquivo **Excel (.xlsx)**  
2. Analisar automaticamente as colunas  
3. Conversar com um **chatbot inteligente** capaz de responder perguntas em linguagem natural sobre os dados

---

## Como instalar e executar

### 1. Baixar o repositório
Clone ou baixe o ZIP do repositório:

```
git clone https://github.com/nielrocha96/PSel.git
cd PSel
```

Ou baixe tudo como ZIP pelo GitHub → *Download ZIP*.

---

### 2. Executar com Docker Compose

Certifique-se de ter **Docker** e **Docker Compose** instalados.

Depois, execute:

```
docker compose up --build
```

Isso irá:

- Construir o container do **backend (FastAPI)**
- Construir o container do **frontend (HTML/JS)**
- Expor o backend em: http://localhost:8000
- Expor o frontend em: http://localhost:8080

Quando ambos estiverem prontos, abra no navegador:

**http://localhost:8080**

---

## Como utilizar a aplicação

### 1. Acesse o frontend

Navegue para:

```
http://localhost:5500
```

Você verá a interface com:

- Botão para enviar o arquivo `.xlsx`
- Caixa de chat para fazer perguntas

---

### 2. Enviar o arquivo Excel

Clique em **Selecionar arquivo**, escolha seu `.xlsx`, depois clique:

**Enviar arquivo**

O backend irá:

- Ler a planilha
- Criar colunas normalizadas (`*_norm`)
- Abrir uma nova sessão
- Retornar o ID da sessão

---

### 3. Fazer perguntas ao chatbot

Depois do upload, você pode perguntar:

```
    Quantos registros existem no arquivo?
    Listar os nomes dos clientes.
    Mostrar os clientes onde o sexo = M.
    Listar todos os veículos vendidos onde marca_veiculo = JEEP.
    Quais são as cores dos veículos vendidos?

    Qual é a soma dos valores de nota?
    Soma de valor_nota onde marca_veiculo = FIAT.
    Total de vendas onde tipo_venda = VD - VENDA DIRETA.
    Somar valor_nota onde movimentacao = VENDA.

    Qual é a média de valor_nota?
    Média do valor_nota onde marca_veiculo = JEEP.
    Média dos valores onde movimentacao = VENDA.
    Média de valor_nota onde cliente_sexo = F.
    Média do valor_nota onde equipe = VENDAS VEICULOS.

    Somar os valores onde funcionario_empresa = UNITED JOÃO XXIII.
    Liste os clientes onde valor_nota > 70000.
    Total de vendas onde cor_veiculo = CINZA SILVERSTONE.
```

O backend identifica automaticamente:

- Intenção (sum, count, list, mean)
- Coluna alvo
- Filtros (com base no texto normalizado)
- Executa a operação e responde

---

## Arquitetura da Aplicação
### Backend (FastAPI)

- Rota `/upload`  
  Recebe o `.xlsx` e cria um `session_id`.

- Rota `/ask`  
  Recebe uma pergunta em linguagem natural e retorna uma resposta baseada nos dados da planilha.

### Frontend (HTML + JS)

- Interface simples para upload
- Chatbox para comunicação
- Envio das perguntas e exibição das respostas

---

## Estrutura do Projeto

```
PSel/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── Dockerfile
│
├── docker-compose.yml
└── README.md
```

---

## Backend — Código Final

O backend utiliza FastAPI e contém:

- Normalização automática de colunas (`*_norm`)
- Extração inteligente de intenção
- Extração automática de colunas com fuzzy matching
- Detecção robusta de filtros
- Execução de operações (`sum`, `mean`, `count`, `list`)

*(O código completo do backend está no arquivo `backend/main.py`.)*

---

## Conclusão

Este projeto fornece um ambiente completo, local e containerizado para análise de planilhas em linguagem natural.

Para rodar:

```
docker compose up --build
```

Depois:

→ abrir `http://localhost:5500`  
→ enviar `.xlsx`  
→ conversar com o chatbot

---
