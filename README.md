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

The `kubernetes-controller` is the juju controller containing the charmed-kubernetes model, 
not the model which holds the `kubernetes-cluster-autoscaler`.

---

```bash
KUBE_CONTROLLER=<kubernetes-controller>
API_ENDPOINTS=$(juju show-controller $KUBE_CONTROLLER --format json | jq -rc '.[].details["api-endpoints"] | join(",")' )
CA_CERT=$(juju show-controller $KUBE_CONTROLLER --format json | jq -rc '.[].details["ca-cert"]' | base64 -w0)
USER=$(juju show-controller $KUBE_CONTROLLER --format json | jq -rc '.[].account.user')
PASSWORD=$(juju show-controller $KUBE_CONTROLLER --show-password --format json | jq -rc '.[].account.password')
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
juju config kubernetes-autoscaler juju_scale="3:5:kubernetes-worker"
```

See below for more complicated examples.

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

## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines
on enhancements to this charm following best practice guidelines, and
`CONTRIBUTING.md` for developer guidance.

[Links]: <>
[kubernetes-auto-scaler]: https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler "upstream docs"
