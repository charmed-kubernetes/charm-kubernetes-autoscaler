# kubernetes-autoscaler

## Description
This charm scales an existing juju deployed kubernetes cluster using the 
[kubernetes cluster autoscaler](kubernetes-auto-scaler) with a juju cloud provider.

## Installation
Installing the charm from charmhub into a kubernetes cluster
```bash
# create a namespace for the autoscaler
juju add-model kubernetes-cluster-autoscaler
# deploy the application into the cluster
juju deploy kubernetes-autoscaler --trust 
```


## Usage
Provide this charm application with credentials to add/remove units from 
an existing juju deployed kubernetes, and the cluster will resize the number
of worker nodes based on the needs of scale. Node groups are defined by
the application name in the deployed model. The autoscaler will not create a cluster, 
but will grow and shrink as demand requires

examples)
```yaml
juju_default_model_uuid: "cdcaed9f-336d-47d3-83ba-d9ea9047b18c" # within this juju model
juju_scale: '- 3:5:kubernetes-worker'          # indicate 3 to 5 kubernetes-worker nodes
```

```yaml
juju_scale: '- 0:10:kubernetes-worker-gpu'   # indicates 0 to 10 nodes of GPU based workers
```

```yaml
# indicates 0 to 10 nodes of GPU based workers and 3 to 5 vanilla worker nodes
juju_scale: '["0:10:kubernetes-worker-gpu","3:5:kubernetes-worker"]'
```

## OCI Images

`rocks.canonical.com/autoscaling/cluster-autoscaler:v1.23.0+juju0`

## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines
on enhancements to this charm following best practice guidelines, and
`CONTRIBUTING.md` for developer guidance.

[Links]: <>
[kubernetes-auto-scaler]: (https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)