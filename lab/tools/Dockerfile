FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    netcat-traditional \
    telnet \
    iputils-ping \
    dnsutils \
    openjdk-11-jdk \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    cassandra-driver \
    pandas \
    requests \
    pyyaml

# Install DSBulk
RUN wget https://downloads.datastax.com/dsbulk/dsbulk-1.10.0.tar.gz && \
    tar -xzf dsbulk-1.10.0.tar.gz && \
    mv dsbulk-1.10.0 /opt/dsbulk && \
    rm dsbulk-1.10.0.tar.gz

# Add DSBulk to PATH
ENV PATH="/opt/dsbulk/bin:${PATH}"

# Create workspace directory
WORKDIR /workspace

# Keep container running
CMD ["tail", "-f", "/dev/null"]