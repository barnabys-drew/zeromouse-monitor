FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY monitor.py .

# uid 1000 matches the typical host user owning the bind-mounted ./data volume
RUN useradd --uid 1000 --create-home monitor
USER monitor

CMD ["python", "-u", "monitor.py"]
