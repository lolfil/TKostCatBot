# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN apt update && apt install gfortran libblas-dev liblapack-dev -y && rm -rf /var/lib/apt/lists/*
RUN pip3 install -r requirements.txt
COPY bot.py .
COPY config_generator.py .

CMD ["python", "bot.py"]