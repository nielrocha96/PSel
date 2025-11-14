# Usa uma imagem Python slim
FROM python:3.10-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia arquivos do backend
COPY . /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta do FastAPI
EXPOSE 8000

# Comando padrão para rodar o uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
