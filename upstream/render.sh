#!/bin/bash
set -eux

RELEASE=$1

# install helm
mkdir -p /root/helm/
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

# render chart
mkdir -p /root/chart/
wget "https://github.com/kubernetes/autoscaler/releases/download/cluster-autoscaler-chart-${RELEASE}/cluster-autoscaler-${RELEASE}.tgz" -O autoscaler.tgz
tar -xvf autoscaler.tgz -C /root/chart/
helm template kubernetes-autoscaler /root/chart/cluster-autoscaler \
    --namespace 'juju-namespace-placeholder' \
    --set 'cloudProvider=juju' | tee /root/rendered.yaml
