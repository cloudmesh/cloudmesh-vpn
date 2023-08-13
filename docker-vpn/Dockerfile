# Use the desired Ubuntu base image
FROM ubuntu:latest

# Update package lists and install dependencies
RUN apt-get update && \
    apt-get install -y dnsutils && \
    apt-get install -y openconnect iputils-ping nano iptables openssh-client openssh-server && \
    apt-get install -y curl python3 python3-pip iproute2 openssh-client openssl git x11-apps net-tools && \
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
RUN cd ~/cm && cloudmesh-installer get vpn

RUN mkdir /app/vscode-1
RUN mkdir /app/vscode-2
RUN mkdir -p /root/.ssh/uva/

RUN setcap cap_net_admin+ep /usr/sbin/openconnect

# Install Visual Studio Code
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository -y "deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main" && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys EB3E94ADBE1229CF && \
    apt-get update && apt-get install -y code


# Set the default command to run when the container starts
CMD ["bash"]
