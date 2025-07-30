# Use uma imagem base oficial do Python
FROM python:3.9

# Defina o diretório de trabalho no contêiner
WORKDIR /usr/src/app

# Copie o arquivo de dependências para o diretório de trabalho
COPY requirements.txt ./

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação para o diretório de trabalho
COPY . .

# Exponha a porta que a aplicação irá rodar
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["python", "-u", "sys_tdm/sys_tdm/manage.py", "runserver", "0.0.0.0:8000"]
