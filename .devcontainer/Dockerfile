FROM python:3.11-slim

RUN apt-get update

RUN apt-get install -y curl netcat-traditional

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt