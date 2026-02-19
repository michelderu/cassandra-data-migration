FROM python:3.11-slim

# Install system dependencies including gnupg for key management
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    netcat-traditional \
    telnet \
    iputils-ping \
    dnsutils \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install OpenJDK 17 from Adoptium using modern gpg approach
RUN mkdir -p /etc/apt/keyrings && \
    wget -O - https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor -o /etc/apt/keyrings/adoptium.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main" | tee /etc/apt/sources.list.d/adoptium.list && \
    apt-get update && \
    apt-get install -y temurin-17-jdk && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages including cqlsh
RUN pip install --no-cache-dir \
    cassandra-driver \
    pandas \
    requests \
    pyyaml \
    cqlsh

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