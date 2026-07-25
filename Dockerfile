# Python 3.11 Slim Image
FROM python:3.11-slim

# Evita que o Python escreva arquivos .pyc e força unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para compilar algumas libs se necessário
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação
COPY . .

# Expõe a porta dinâmica configurada pelo Railway (Padrão 8080)
EXPOSE 8080

# Comando de inicialização unificado modo dashboard
CMD ["python", "run.py", "--mode", "dashboard"]
