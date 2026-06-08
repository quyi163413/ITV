#!/bin/bash
# 多架构构建并推送（可选）
# 使用 buildx 构建支持 amd64 和 arm64 的镜像

# 设置镜像名称和标签
IMAGE_NAME="iptv-collector"
TAG="latest"

# 启用 buildx
docker buildx create --use --name multiarch-builder || true
docker buildx inspect --bootstrap

# 构建多架构镜像（本地不推送时使用 --load 只支持单平台，要推送需使用 --push）
# 仅构建当前架构（适用于本地测试）
docker buildx build --platform linux/amd64,linux/arm64 -t ${IMAGE_NAME}:${TAG} --load . 2>&1 | tee build.log

# 如果想把镜像推送到仓库（如 Docker Hub），取消注释以下行：
# docker buildx build --platform linux/amd64,linux/arm64 -t yourusername/${IMAGE_NAME}:${TAG} --push .
