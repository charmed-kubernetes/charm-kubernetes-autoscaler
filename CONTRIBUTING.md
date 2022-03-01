# kubernetes-autoscaler

## Developing
Creates and runs unit testing and linting:

```bash
tox -e unit,lint
```

Run integration tests by switching to a kubernetes cluster

```bash
juju controllers k8s-controller
tox -e integration
```

Format code with black

```bash
tox -e blacken
```

## Test installation locally
```bash
charmcraft pack
CHARM=$(ls *.charm)
IMAGE=$(cat metadata.yaml |\
        python3 -c 'import yaml; import sys; import json; print(json.dumps(yaml.safe_load(sys.stdin)))' |\
        jq -rc '.resources["juju-autoscaler-image"]["upstream-source"]')
# create a namespace for the autoscaler
juju add-model kubernetes-cluster-autoscaler
# deploy the application into the cluster
juju deploy ./$CHARM kubernetes-autoscaler --trust --resource juju-autoscaler-image=$IMAGE
# configure the charm according to README.md
```

## Intended use case

This charm handles deploying a bare kubernetes cluster-autoscaler able to grow
and shrink a configured juju-based kubernetes cluster.

## Roadmap
There is an intention to expand this charms feature-set to include:
* monitoring, 
* statistics, 
* an exposed service

Eventually it should be expanded to deploy just as the upstream helm charts suggest
with the juju cloud-provider mainlined into the upstream source.
