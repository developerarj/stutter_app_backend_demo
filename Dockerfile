# Use an official Ubuntu image as a parent image
FROM ubuntu:20.04

# Add the deadsnakes PPA for Python 3.11
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    wget \
    ffmpeg \
    libssl-dev \
    ca-certificates \
    iputils-ping \
    openssl \
    ntp \
    && apt-get install --fix-missing \
    && rm -rf /var/lib/apt/lists/*

# Set up Python 3.11 as the default python interpreter
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Download and install pip for Python 3.11
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python3.11 get-pip.py && \
    rm get-pip.py

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Copy .env file to the container
COPY .env /app

# Set environment variables
ENV FLASK_ENV=development

# Install any needed dependencies specified in requirements.txt
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# Ensure CA certificates are up to date
RUN apt-get update && apt-get install -y ca-certificates

# Define volumes for file uploads
VOLUME ["/app/files/audioFiles", "/app/files/modal", "/app/files/user"]

# Make port 5000 available to the world outside this container
EXPOSE 80

# Run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "run:app"]
