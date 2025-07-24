FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt* ./

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn[standard]

RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY . .

EXPOSE 10001

CMD ["uvicorn", "Fastapitest:app", "--reload", "--host", "0.0.0.0", "--port", "10001"]