# How to build the hotel reservation multi-architecture image

## install docker
```
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get update
sudo apt-get install     apt-transport-https     ca-certificates     curl     gnupg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo   "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
```

## install buildx
```
sudo apt-get install binfmt-support qemu-user-static
sudo apt-get install jq
mkdir -p ~/.docker/cli-plugins
curl https://api.github.com/repos/docker/buildx/releases/latest | jq -r '.assets[].browser_download_url' | grep amd64

BUILDX_URL=https://github.com/docker/buildx/releases/download/v0.5.1/buildx-v0.5.1.linux-amd64
wget $BUILDX_URL -O ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
```
 
## create a multi-arch builder
```
docker buildx create --name mbuilder
docker buildx use mbuilder
docker buildx inspect --bootstrap
[+] Building 6.3s (1/1) FINISHED
=> [internal] booting buildkit                                                             6.3s
=> => pulling image moby/buildkit:buildx-stable-1                                          4.5s
=> => creating container buildx_buildkit_mbuilder0                                         1.8s
Name:   mbuilder
Driver: docker-container
Nodes:
Name:      mbuilder0
Endpoint:  unix:///var/run/docker.sock
Status:    running
Platforms: linux/amd64, linux/arm64, linux/riscv64, linux/ppc64le, linux/s390x, linux/386, linux/arm/v7, linux/arm/v6
```
 
## get DeathStarBench repo
```
git clone https://github.com/delimitrou/DeathStarBench.git
```

## log in to docker hub as user: cesgsw
```
docker login
```

## build and push image to docker hub
```
cd DeathStarBench/hotelReservation
docker buildx build --platform linux/amd64,linux/arm64 -t cesgsw/dsb-hotel-reservation-microservices:v1.0 --push .
```
 
## inspect the image
```
docker buildx imagetools inspect cesgsw/dsb-hotel-reservation-microservices:v1.0
Name:      docker.io/cesgsw/dsb-hotel-reservation-microservices:v1.0
MediaType: application/vnd.docker.distribution.manifest.list.v2+json
Digest:    sha256:4f2ff1055fae2dfff882912aa3399f34670cd87deaabf724e1b64ecc107d5340

Manifests:
  Name:      docker.io/cesgsw/dsb-hotel-reservation-microservices:v1.0@sha256:af4b176f3bea7ac94d4f6404affd5348b9c51be7252d4bc16fb084520e831332
  MediaType: application/vnd.docker.distribution.manifest.v2+json
  Platform:  linux/amd64

  Name:      docker.io/cesgsw/dsb-hotel-reservation-microservices:v1.0@sha256:096fa77ac9f424fe1b7a2463203840d3a13bd83f65f41404b32a524bfae1351a
  MediaType: application/vnd.docker.distribution.manifest.v2+json
  Platform:  linux/arm64