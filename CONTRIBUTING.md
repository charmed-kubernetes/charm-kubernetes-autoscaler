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
