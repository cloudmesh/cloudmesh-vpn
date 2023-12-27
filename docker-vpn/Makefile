DOCKER_IMAGE_NAME = $(VPN)-vpn-image
DISPLAY := $(shell route.exe print | grep 0.0.0.0 | head -1 | awk '{print $$4}'):0.0

build setup:
	docker build -t $(DOCKER_IMAGE_NAME) .

run shell:
	@if docker ps -q -f name=$(VPN)-vpn-container | grep -q . ; then \
		echo "Container is already running. Attaching..." ; \
		docker exec -it $(VPN)-vpn-container bash ; \
	else \
		echo "Container is not running. Starting new container..." ; \
		docker run -it --privileged --detach --name $(VPN)-vpn-container --cap-add=NET_ADMIN \
		-v $(PWD):/app -v ~/remote_mount:/app/remote_mount $(DOCKER_IMAGE_NAME) ; \
	fi

clean delete remove rm stop:
	docker stop $(VPN)-vpn-container
	docker rm $(VPN)-vpn-container

build-ufl:
	docker build -t ufl-vpn-image .

shell-ufl run-ufl:
	echo "display is $(DISPLAY)"
	@if docker ps -q -f name=ufl-vpn-container | grep -q . ; then \
		echo "Container is already running. Attaching..." ; \
		docker exec -it -e DISPLAY=$(DISPLAY) -e DONT_PROMPT_WSL_INSTALL=y ufl-vpn-container bash ; \
	else \
		echo "Container is not running. Starting new container..." ; \
		docker run -it --privileged --detach --name ufl-vpn-container --cap-add=NET_ADMIN --net=host \
		--env DISPLAY=${DISPLAY} --env DONT_PROMPT_WSL_INSTALL=y -v $(PWD):/app -v ~/remote_mount:/app/remote_mount ufl-vpn-image ; \
	fi

build-uva:
	docker build --no-cache -t uva-vpn-image .

shell-uva run-uva:
# this is potentially a bad idea because of that backslash after home.
	echo "display is $(DISPLAY)"
	
	@if docker ps -q -f name=uva-vpn-container | grep -q . ; then \
		echo "Container is already running. Attaching..." ; \
		docker exec -it -e DISPLAY=$(DISPLAY) -e DONT_PROMPT_WSL_INSTALL=y \
		uva-vpn-container bash ; \
	else \
		echo "Container is not running. Starting new container..." ; \
		docker run -it --privileged --detach --name uva-vpn-container --cap-add=NET_ADMIN --net=host \
		--env DISPLAY=${DISPLAY} --env DONT_PROMPT_WSL_INSTALL=y -v $(PWD):/app \
		-v "${HOME}\.cloudmesh":/root/.cloudmesh -v ~/remote_mount:/app/remote_mount uva-vpn-image ; \
	fi
