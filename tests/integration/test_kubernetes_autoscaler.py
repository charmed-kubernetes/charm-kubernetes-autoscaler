import base64
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Optional
import pytest
import yaml

log = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy_autoscaler_charm(ops_test, k8s_model):
    _, k8s_alias = k8s_model
    connection = ops_test.model.connection()
    cacert = base64.b64encode(connection.cacert.encode("ascii")).decode("ascii")
    xtra_args = "{v: 5, scale-down-delay-after-add: 3m0s, scale-down-unneeded-time: 3m0s}"
    juju_args = {
        "juju_api_endpoints": connection.endpoint,
        "juju_ca_cert": cacert,
        "juju_default_model_uuid": connection.uuid,
        "juju_username": connection.username,
        "juju_password": connection.password,
        "juju_scale": "- {min: 1, max: 2, application: kubernetes-worker}",
        "autoscaler_extra_args": xtra_args,
    }

    metadata = yaml.safe_load(Path("metadata.yaml").read_text())
    image = metadata["resources"]["juju-autoscaler-image"]["upstream-source"]

    with ops_test.model_context(k8s_alias) as k8s_model:
        charm = next(Path(".").glob("kubernetes-autoscaler*.charm"), None)
        if not charm:
            log.info("Build Charm...")
            charm = await ops_test.build_charm(".")

        await k8s_model.deploy(
            entity_url=charm.resolve(),
            trust=True,
            config=juju_args,
            resources={"juju-autoscaler-image": image},
        )

        await k8s_model.block_until(
            lambda: "kubernetes-autoscaler" in k8s_model.applications, timeout=60
        )

        await k8s_model.wait_for_idle(status="active")


async def test_status_autoscaler_charm(units):
    assert units[0].workload_status == "active"
    assert units[0].workload_status_message == ""


async def wait_for_worker_count(model, expected_workers):
    """
    Blocks waiting for worker count within the model to reach the expected number.

    checks every half a second if the model has the required number of worker units.
    Logs a message every 30 seconds about the number of workers
    """
    last_log_time: Optional[datetime] = None
    log_interval = timedelta(seconds=30)

    def condition():
        nonlocal last_log_time
        unit_count = len(model.applications["kubernetes-worker"].units)
        if last_log_time is None or (datetime.now() - last_log_time) > log_interval:
            log.info(f"Worker count {unit_count} != {expected_workers}... ")
            last_log_time = datetime.now()
        elif unit_count == expected_workers:
            log.info(f"Worker count reached {unit_count}")
        return unit_count == expected_workers

    await model.block_until(condition, timeout=15 * 60)


async def test_scale_up(scaled_up_deployment, ops_test):
    log.info("Watching workers expand...")
    assert len(ops_test.model.applications["kubernetes-worker"].units) == 1
    await wait_for_worker_count(ops_test.model, 2)
    await ops_test.model.wait_for_idle(status="active", timeout=15 * 60)


async def test_scale_down(scaled_down_deployment, ops_test):
    log.info("Watching workers contract...")
    assert len(ops_test.model.applications["kubernetes-worker"].units) == 2
    await wait_for_worker_count(ops_test.model, 1)
    await ops_test.model.wait_for_idle(status="active", timeout=15 * 60)
