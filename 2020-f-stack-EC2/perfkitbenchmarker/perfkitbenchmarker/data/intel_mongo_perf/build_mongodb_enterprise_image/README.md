# How to build the multi-arch MongoDB Enterprise image using Docker Desktop for Windows and WSL2

## Create and select a builder
```
$ docker buildx create --name mybuilder --use --driver-opt env.http_proxy=$http_proxy --driver-opt env.https_proxy=$https_proxy 
```

## Verify and load the builder
```
$ docker buildx inspect –bootstrap 
```

## Build the image
Note: The MongoDB version is hard-coded in the Dockerfile.

This step can be executed by running build_enterprise_image.sh.
```
$ docker buildx build \ 
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
-t cesgsw/mongo-enterprise:4.4.1 \ 
. 
```

