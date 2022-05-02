# kubernetes-autoscaler

## Description
This charm scales an existing juju deployed kubernetes cluster using the 
[kubernetes cluster autoscaler][kubernetes-auto-scaler] with a juju cloud provider.

## Installation
Installing the charm from charmhub into a kubernetes cluster
```bash
# create a namespace for the autoscaler
juju add-model kubernetes-cluster-autoscaler
# deploy the application into the cluster
juju deploy kubernetes-autoscaler --trust 
```

## Usage/Configuration
Provide this charm application with credentials to add/remove units from 
an existing juju deployed kubernetes, and the cluster will resize the number
of worker nodes based on the needs of scale. Node groups are defined by
the application name in the deployed model. The autoscaler will not create a cluster, 
but will grow and shrink as demand requires

### Setting controller config
You can retrieve the necessary configuration information with the following commands.

---
**NOTE:**
The `kubernetes-controller` is the juju controller which holds the charmed-kubernetes model, 
not the model which holds the `kubernetes-autoscaler`.
---

```bash
KUBE_CONTROLLER=<kubernetes-controller>
API_ENDPOINTS=$(
    juju show-controller $KUBE_CONTROLLER --format json |
    jq -rc '.[].details["api-endpoints"] |
    join(",")'
)
CA_CERT=$(
    juju show-controller $KUBE_CONTROLLER --format json |
    jq -rc '.[].details["ca-cert"]' |
    base64 -w0
)
USER=$(
    juju show-controller $KUBE_CONTROLLER --format json |
    jq -rc '.[].account.user'
)
PASSWORD=$(
    juju show-controller $KUBE_CONTROLLER --show-password --format json |
    jq -rc '.[].account.password'
)
```

The autoscaler is recommended to run on a control-plane node so that it isn't reaped when a worker node is scaled
down. Ensure the control-plane nodes do not have the taint `juju.is/kubernetes-control-plane=true:NoSchedule` applied
so that they can run pods.
```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints --no-headers 
```

In order to remove the taint, for each control-plane node run:
```bash
kubectl taint node $NODE juju.is/kubernetes-control-plane=true:NoSchedule- 
```

Deploy the charm into a `k8s` type juju model (not a machine model)
```bash
juju deploy kubernetes-autoscaler --constraints "tags=node.juju-application=kubernetes-control-plane"
```

Provide these as configuration to the deployed application
```bash
juju config kubernetes-autoscaler \
    juju_api_endpoints="${API_ENDPOINTS}" \
    juju_ca_cert="${CA_CERT}"\
    juju_username="${USER}"\
    juju_password="${PASSWORD}"
```

After this, you'll need to find the model which contains the application to scale
```bash
juju models -c $KUBE_CONTROLLER --format json | jq -cr '.models[]|{name,"model-uuid"}'
```

Using the correct `model-uuid`, set the `default_model_uuid`.

```bash
juju config kubernetes-autoscaler juju_default_model_uuid=$MODEL_UUID
```

Lastly, pick the worker application to scale. Usually this is `kubernetes-worker`.

```bash
juju config kubernetes-autoscaler juju_scale="- {min: 3, max: 5, application: kubernetes-worker}"
```

See below for more complicated examples.

```yaml
juju_default_model_uuid: "cdcaed9f-336d-47d3-83ba-d9ea9047b18c"   # within this juju model
juju_scale: '- {min: 3, max: 5, application: kubernetes-worker}'  # indicates 3 to 5 kubernetes-worker nodes
```

```yaml
# indicates 0 to 10 nodes of GPU based workers
juju_scale: '- {min: 1, max: 10, application: kubernetes-worker-gpu}'
```

```yaml
# indicates 0 to 10 nodes of GPU based workers and 3 to 5 kubernetes-worker nodes
juju_scale: |-
   - {min: 1, max: 10, application: kubernetes-worker-gpu}
   - {min: 3, max: 5, application: kubernetes-worker}
```

Be sure that the yaml presented in `juju_scale` is valid json or yaml.

## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines
on enhancements to this charm following best practice guidelines, and
`CONTRIBUTING.md` for developer guidance.

[Links]: <>
[kubernetes-auto-scaler]: https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler "upstream docs"
