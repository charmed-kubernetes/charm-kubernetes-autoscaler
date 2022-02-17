import logging
import shlex
import pytest

log = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test):
    juju_info = await ops_test._controller.info()
    juju_args = {
        "juju_api_endpoints": ",".join(
            addr for _ in juju_info["results"] for addr in _["addresses"]
        ),
        "juju_ca_cert": juju_info["results"][0]["cacert"],
        "juju_model_uuid": ops_test.model.uuid,
        "juju_username": "alice",
        "juju_password": "bob",
    }

    log.info("Build Charm...")
    charm = await ops_test.build_charm(".")

    log.info("Render Bundle...")
    bundle = ops_test.render_bundle("tests/data/bundle.yaml", charm=charm, juju_args=juju_args)

    log.info("Deploy Charm...")
    model = ops_test.model_full_name
    cmd = f"juju deploy -m {model} {bundle}"
    rc, stdout, stderr = await ops_test.run(*shlex.split(cmd))
    assert rc == 0, f"Bundle deploy failed: {(stderr or stdout).strip()}"

    log.info(stdout)
    await ops_test.model.block_until(
        lambda: "kubernetes-autoscaler" in ops_test.model.applications, timeout=60
    )

    await ops_test.model.wait_for_idle(wait_for_active=True)


async def test_status(units):
    assert units[0].workload_status == "active"
    assert units[0].workload_status_message == "Ready to Scale"
