FROM python:3.12-slim
WORKDIR /app
COPY services/naming/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
ENV PYTHONPATH=/app
CMD ["uvicorn", "services.naming.app.main:app", "--host", "0.0.0.0", "--port", "8020"]
