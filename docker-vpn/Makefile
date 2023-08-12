DOCKER_CONTAINER_NAME = my-vpn-container
DOCKER_IMAGE_NAME = vpn-image


build setup:
	docker build -t vpn-image .

run shell:
	@if docker ps -q -f name=$(DOCKER_CONTAINER_NAME) | grep -q . ; then \
		echo "Container is already running. Attaching..." ; \
		docker exec -it $(DOCKER_CONTAINER_NAME) bash ; \
	else \
		echo "Container is not running. Starting new container..." ; \
		docker run -it --privileged --detach --name $(DOCKER_CONTAINER_NAME) --cap-add=NET_ADMIN \
		-v $(PWD):/app -v ~/remote_mount:/app/remote_mount $(DOCKER_IMAGE_NAME) ; \
	fi

clean delete remove rm stop:
	docker stop my-vpn-container
	docker rm my-vpn-container
