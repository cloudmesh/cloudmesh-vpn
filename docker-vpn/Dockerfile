# Use the desired Ubuntu base image
FROM ubuntu:latest

# Update package lists and install dependencies
RUN apt-get update && \
    apt-get install -y dnsutils && \
    apt-get install -y openconnect && \
    apt-get install -y curl python3 python3-pip iproute2 openssh-client openssl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up a working directory
WORKDIR /app

# Copy the script into the container
# COPY setup.py /app
COPY requirements.txt /app

RUN pip install -r requirements.txt

# RUN mkdir /app/remote-mount
RUN mkdir ~/cm
RUN cd ~/cm && cloudmesh-installer get cc

# # Install Visual Studio Code
# RUN apt-get update && apt-get install -y software-properties-common && \
#     add-apt-repository -y "deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main" && \
#     apt-key adv --keyserver keyserver.ubuntu.com --recv-keys EB3E94ADBE1229CF && \
#     apt-get update && apt-get install -y code


# Set the default command to run when the container starts
CMD ["bash"]
