import base64
import logging
import shlex
from pathlib import Path
import pytest
import yaml

log = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test, k8s_model):
    _, k8s_alias = k8s_model
    connection = ops_test.model.connection()
    cacert = base64.b64encode(connection.cacert.encode("ascii")).decode("ascii")
    juju_args = {
        "juju_api_endpoints": connection.endpoint,
        "juju_ca_cert": cacert,
        "juju_default_model_uuid": connection.uuid,
        "juju_username": connection.username,
        "juju_password": connection.password,
        "juju_scale": "- {min: 1, max: 2, application: kubernetes-worker}",
    }

    metadata = yaml.safe_load(Path("metadata.yaml").read_text())
    image = metadata["resources"]["juju-autoscaler-image"]["upstream-source"]

    with ops_test.model_context(k8s_alias) as k8s_model:
        log.info("Build Charm...")
        charm = await ops_test.build_charm(".")

        log.info("Render Bundle...")
        bundle = ops_test.render_bundle(
            "tests/data/bundle.yaml", charm=charm, juju_args=juju_args, juju_autoscaler_image=image
        )

        log.info("Deploy Charm...")
        cmd = f"juju deploy {bundle} --trust"
        rc, stdout, stderr = await ops_test.run(*shlex.split(cmd))
        assert rc == 0, f"Bundle deploy failed: {(stderr or stdout).strip()}"

        log.info(stdout)
        await k8s_model.block_until(
            lambda: "kubernetes-autoscaler" in k8s_model.applications, timeout=60
        )

        await k8s_model.wait_for_idle(wait_for_active=True)


async def test_status(units):
    assert units[0].workload_status == "active"
    assert units[0].workload_status_message == ""


async def test_scale_up(scaled_up_deployment, ops_test):
    await ops_test.model.wait_for_idle(wait_for_active=True, timeout=15 * 60)
    assert len(ops_test.model.applications["kubernetes-worker"].units) == 2


async def test_scale_down(scaled_down_deployment, ops_test):
    def conditions():
        return len(ops_test.model.applications["kubernetes-worker"].units) == 1

    await ops_test.model.block_until(conditions, timeout=15 * 60)
