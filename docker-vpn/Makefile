DOCKER_IMAGE_NAME = vpn-image

build setup:
	docker build -t $(VPN)-$(DOCKER_IMAGE_NAME) .

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
