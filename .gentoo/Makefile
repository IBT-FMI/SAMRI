# We must allow others exactly use our script without modification
# Or its not replicable by others.
#
REGISTRY=docker.io
REPOSITORY=centerforopenneuroscience

IMAGE_NAME=samri
IMAGE_TAG=0.0.1

FQDN_IMAGE=${REGISTRY}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}

OCI_BINARY?=podman
RELEASE_VERSION?=9999
RESOLUTION?=9999 # specified in microns

DISTFILE_CACHE_CMD :=

check_defined = \
	$(strip $(foreach 1,$1, \
	$(call __check_defined,$1,$(strip $(value 2)))))
__check_defined = \
	$(if $(value $1),, \
	$(error Undefined $1$(if $2, ($2))))

ifeq ($(DISTFILE_CACHE_PATH),)
	# If not set, don't add it as an option
else
	DISTFILE_CACHE_CMD =-v $(DISTFILE_CACHE_PATH):/var/cache/distfiles
endif

.PHONY: interactive-oci-image
interactive-oci-image:
	$(OCI_BINARY) run \
		-it \
		--rm \
		-v ${PWD}/..:/opt/SAMRI
		--workdir /root/ \
		${FQDN_IMAGE} \
		/bin/bash

.PHONY: oci-image
oci-image:
	$(OCI_BINARY) build ../ $(DISTFILE_CACHE_CMD) \
		-f Containerfile \
		-t ${FQDN_IMAGE}

.PHONY: oci-push
oci-push:
	$(OCI_BINARY) push ${FQDN_IMAGE}
