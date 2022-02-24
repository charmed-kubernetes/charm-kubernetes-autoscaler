#!/bin/bash
set -eux

VERSION="${1:-$(python3 version.py)}"
echo $VERSION > version
lxc launch ubuntu:20.04 helm
trap "lxc delete helm --force" EXIT
sleep 5;
lxc file push render.sh helm/root/
lxc exec helm /root/render.sh $VERSION
lxc file pull helm/root/rendered.yaml manifests/rendered.yaml