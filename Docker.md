# Docker setup instructions for Raspberry Pi

1. Install Docker on the pis:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi
sudo reboot
```

2. Upgrade libseccomp (to work with updated APT repos on the base Ubuntu 20.04 images):

```bash
wget http://ftp.us.debian.org/debian/pool/main/libs/libseccomp/libseccomp2_2.5.1-1_armhf.deb
sudo dpkg -i libseccomp2_2.5.1-1_armhf.deb
```

# Cross-compilation on hosts

1. Make sure Docker Buildx is installed.

2. Create a custom builder for cross-compilation (only need to do this once):

```bash
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```

3. Build the multiarch images and push:

```bash
docker buildx build --push --platform=linux/armhf,linux/amd64 -t molguin/cleave:base --target base .
docker buildx build --push --platform=linux/armhf,linux/amd64 -t molguin/cleave:cleave --target cleave .
```
