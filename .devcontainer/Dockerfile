FROM docker.io/library/debian:trixie-slim

RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    bash \
    btop \
    build-essential \
    ca-certificates \
    curl \
    gdb \
    gettext \
    git \
    less \
    libpq-dev \
    ncdu \
    openssh-client \
    postgresql-client \
    sudo \
    tzdata \
    vim \
    wget \
    zsh \
    && \
    apt-get autoclean -y \
    && \
    apt-get autoremove -y \
    && \
    rm -rf /var/lib/apt/lists/* \
    2>&1

RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid 1000 -s /bin/zsh -m vscode \
    && mkdir -p /run/user/1000 \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode \
    && touch /home/vscode/.zshrc

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# VOLUME [ "/home" ]

# Switch to vs code user
# USER vscode
# WORKDIR /workspace

# Set /workspace as a safe git directory
# RUN git config --global --add safe.directory /workspace

# Back to root
# USER root

