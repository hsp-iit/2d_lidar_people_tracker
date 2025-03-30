#!/bin/bash
NAME=convince_people_detector
TAG=latest

xhost +
docker run \
     --network=host --privileged \
     -it \
     --rm \
     --gpus all \
     -e DISPLAY=unix${DISPLAY} \
     -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID} \
     --device /dev/dri/card0:/dev/dri/card0 \
     -v /tmp/.X11-unix:/tmp/.X11-unix \
     ${NAME}:${TAG} bash
