FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаем директорию для ключей (ключи будут смонтированы через volumes)
RUN mkdir -p /app/keys

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY entrypoint_fixed.sh .

RUN chmod +x entrypoint_fixed.sh

CMD ["./entrypoint_fixed.sh"]
