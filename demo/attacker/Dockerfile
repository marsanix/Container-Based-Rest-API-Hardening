FROM kalilinux/kali-rolling:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    dsniff \
    tcpdump \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*
