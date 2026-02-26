FROM python:3.12-slim

ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_MIRROR_URL=${PIP_INDEX_URL}

# Install required tools
RUN apt-get update && \
    apt-get install -y curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all files into container
COPY . .

# Set execute permissions on script
RUN chmod +x plugin_repackaging.sh

# Set default command
CMD ["./plugin_repackaging.sh", "-p", "manylinux_2_17_x86_64", "market", "antv", "visualization", "0.1.7"]
