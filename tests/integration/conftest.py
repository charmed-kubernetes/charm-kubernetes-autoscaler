import logging
import pytest
import pytest_asyncio
import os
import random
import string
from pathlib import Path
from types import SimpleNamespace
import yaml

from lightkube import KubeConfig, Client
from lightkube.resources.core_v1 import Namespace
from lightkube.models.meta_v1 import ObjectMeta


log = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="module")
async def charmed_kubernetes(ops_test):
    with ops_test.model_context("main") as model:
        deploy, control_plane_app = True, "kubernetes-control-plane"
        current_model = ops_test.request.config.option.model
        if current_model:
            control_plane_apps = [
                app_name
                for app_name, app in model.applications.items()
                if "kubernetes-control-plane" in app.charm_url
            ]
            if not control_plane_apps:
                pytest.fail(f"Model {current_model} doesn't contain {control_plane_app} charm")
            deploy, control_plane_app = False, control_plane_apps[0]

        if deploy:
            await model.deploy("kubernetes-core", channel="latest/edge")
        await model.wait_for_idle(wait_for_active=True, timeout=60 * 60)
        kubeconfig_path = ops_test.tmp_path / "kubeconfig"
        retcode, stdout, stderr = await ops_test.run(
            "juju",
            "scp",
            f"{control_plane_app}/leader:.kube/config",
            kubeconfig_path,
        )
        if retcode != 0:
            log.error(f"retcode: {retcode}")
            log.error(f"stdout:\n{stdout.strip()}")
            log.error(f"stderr:\n{stderr.strip()}")
            pytest.fail("Failed to copy kubeconfig from kubernetes-control-plane")
    yield SimpleNamespace(kubeconfig=kubeconfig_path, model=model)


@pytest_asyncio.fixture(scope="module")
async def k8s_cloud(charmed_kubernetes, ops_test):
    """Use an existing k8s-cloud or create a k8s-cloud for deploying a new k8s model into"""
    cloud_name = "k8s-cloud"
    controller = await ops_test.model.get_controller()
    current_clouds = await controller.clouds()
    if f"cloud-{cloud_name}" in current_clouds.clouds:
        yield cloud_name
        return

    with ops_test.model_context("main"):
        os.environ["KUBECONFIG"] = str(charmed_kubernetes.kubeconfig)
        await ops_test.juju(
            "add-k8s",
            cloud_name,
            "--skip-storage",
            "--controller",
            ops_test.controller_name,
            "--client",
        )
    yield cloud_name

    with ops_test.model_context("main"):
        if not ops_test.keep_model:
            await ops_test.juju(
                "remove-cloud", cloud_name, "--controller", ops_test.controller_name, "--client"
            )


@pytest_asyncio.fixture(scope="module")
async def k8s_model(k8s_cloud, ops_test):
    model_alias = "k8s-cloud"
    await ops_test.add_model(model_alias, cloud_name=k8s_cloud)
    yield model_alias
    await ops_test.remove_model(model_alias)


@pytest_asyncio.fixture(scope="module")
async def kubernetes(charmed_kubernetes, request):
    namespace = request.node.name + "-" + random.choice(string.ascii_lowercase + string.digits) * 5
    config = KubeConfig.from_file(charmed_kubernetes.kubeconfig)
    client = Client(
        config=config.get(context_name="juju-context"),
        namespace=namespace,
        trust_env=False,
    )
    namespace_obj = Namespace(metadata=ObjectMeta(name=namespace))
    client.create(namespace_obj)
    yield client
    client.delete(Namespace, namespace)


@pytest.fixture
def metadata():
    metadata = Path("./metadata.yaml")
    data = yaml.safe_load(metadata.read_text())
    return data


@pytest.fixture
def model(k8s_model, ops_test):
    with ops_test.model_context(k8s_model) as model:
        pass
    return model


@pytest.fixture
def application(model, metadata):
    charm_name = metadata["name"]
    app = model.applications[charm_name]
    return app


@pytest.fixture
def units(application):
    units = application.units
    return units
