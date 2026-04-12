FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir requests

COPY monitor.py .

CMD ["python", "-u", "monitor.py"]
