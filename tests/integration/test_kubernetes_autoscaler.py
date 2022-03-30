import base64
import logging
import shlex
from pathlib import Path
import pytest
import yaml

log = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test):
    connection = ops_test.model.connection()
    cacert = base64.b64encode(connection.cacert.encode("ascii")).decode("ascii")
    juju_args = {
        "juju_api_endpoints": connection.endpoint,
        "juju_ca_cert": cacert,
        "juju_default_model_uuid": connection.uuid,
        "juju_username": connection.username,
        "juju_password": connection.password,
        "juju_scale": "- {min: 0, max: 2, application: scale-app}",
    }

    metadata = yaml.safe_load(Path("metadata.yaml").read_text())
    image = metadata["resources"]["juju-autoscaler-image"]["upstream-source"]

    log.info("Build Charm...")
    charm = await ops_test.build_charm(".")

    log.info("Render Bundle...")
    bundle = ops_test.render_bundle(
        "tests/data/bundle.yaml", charm=charm, juju_args=juju_args, juju_autoscaler_image=image
    )

    log.info("Deploy Charm...")
    model = ops_test.model_full_name
    cmd = f"juju deploy -m {model} {bundle} --trust"
    rc, stdout, stderr = await ops_test.run(*shlex.split(cmd))
    assert rc == 0, f"Bundle deploy failed: {(stderr or stdout).strip()}"

    log.info(stdout)
    await ops_test.model.block_until(
        lambda: "kubernetes-autoscaler" in ops_test.model.applications, timeout=60
    )

    await ops_test.model.wait_for_idle(wait_for_active=True)


async def test_status(units):
    assert units[0].workload_status == "active"
    assert units[0].workload_status_message == ""
