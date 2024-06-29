#! /bin/bash
docker buildx build \
--build-arg https_proxy=$https_proxy \
--build-arg http_proxy=$http_proxy \
--build-arg no_proxy=$no_proxy \
--build-arg HTTPS_PROXY=$https_proxy \
--build-arg HTTP_PROXY=$http_proxy \
--build-arg NO_PROXY=$no_proxy \
--build-arg MONGO_PACKAGE=mongodb-enterprise \
--build-arg MONGO_REPO=repo.mongodb.com \
--platform linux/arm64/v8,linux/amd64 \
--push \
-t cesgsw/mongo-enterprise:4.4.1 .
