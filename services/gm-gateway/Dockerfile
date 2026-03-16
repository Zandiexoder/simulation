FROM python:3.12-slim
WORKDIR /app
COPY services/gm-gateway/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
ENV PYTHONPATH=/app
CMD ["uvicorn", "app.main:app", "--app-dir", "services/gm-gateway", "--host", "0.0.0.0", "--port", "8010"]
