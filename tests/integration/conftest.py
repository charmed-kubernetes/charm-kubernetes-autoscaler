import logging

import pytest
import pytest_asyncio
from _pytest.config.argparsing import Parser
import random
import string
from pathlib import Path
from types import SimpleNamespace
import yaml

from lightkube import KubeConfig, Client, codecs
from lightkube.resources.core_v1 import Namespace
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.apps_v1 import Deployment
from lightkube.models.autoscaling_v1 import ScaleSpec

log = logging.getLogger(__name__)


def pytest_addoption(parser: Parser):
    parser.addoption(
        "--k8s-cloud",
        action="store",
        help="Juju kubernetes cloud to reuse; if not provided, will generate a new cloud",
    )


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
            f"{control_plane_app}/leader:/home/ubuntu/config",
            kubeconfig_path,
        )
        if retcode != 0:
            log.error(f"retcode: {retcode}")
            log.error(f"stdout:\n{stdout.strip()}")
            log.error(f"stderr:\n{stderr.strip()}")
            pytest.fail("Failed to copy kubeconfig from kubernetes-control-plane")
        assert Path(kubeconfig_path).stat().st_size, "kubeconfig file is 0 bytes"
    yield SimpleNamespace(kubeconfig=kubeconfig_path, model=model)


@pytest_asyncio.fixture(scope="module")
async def k8s_cloud(charmed_kubernetes, ops_test, request):
    """Use an existing k8s-cloud or create a k8s-cloud for deploying a new k8s model into"""
    cloud_name = (
        request.config.option.k8s_cloud or f"{request.module.__name__.replace('_', '-')}-k8s-cloud"
    )
    controller = await ops_test.model.get_controller()
    current_clouds = await controller.clouds()
    if f"cloud-{cloud_name}" in current_clouds.clouds:
        yield cloud_name
        return

    with ops_test.model_context("main"):
        log.info(f"Adding cloud '{cloud_name}'...")
        kubeconfig = charmed_kubernetes.kubeconfig.read_bytes()
        await ops_test.juju(
            "add-k8s",
            cloud_name,
            "--skip-storage",
            f"--controller={ops_test.controller_name}",
            "--client",
            check=True,
            stdin=kubeconfig,
            fail_msg=f"Failed to add-k8s {cloud_name}",
        )
    yield cloud_name

    with ops_test.model_context("main"):
        log.info(f"Removing cloud '{cloud_name}'...")
        await ops_test.juju(
            "remove-cloud",
            cloud_name,
            "--controller",
            ops_test.controller_name,
            "--client",
            check=True,
        )


@pytest_asyncio.fixture(scope="module")
async def kubernetes(charmed_kubernetes, request):
    namespace = (
        request.module.name + "-" + random.choice(string.ascii_lowercase + string.digits) * 5
    )
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


@pytest_asyncio.fixture(scope="module")
async def k8s_model(k8s_cloud, ops_test):
    model_alias = "k8s-model"
    model = await ops_test.track_model(
        model_alias, cloud_name=k8s_cloud, credential_name=k8s_cloud
    )
    yield model, model_alias
    await ops_test.forget_model(model_alias, timeout=5 * 60)


@pytest.fixture
def metadata():
    metadata = Path("./metadata.yaml")
    data = yaml.safe_load(metadata.read_text())
    return data


@pytest.fixture
def application(k8s_model, metadata):
    model, alias = k8s_model
    charm_name = metadata["name"]
    return model.applications[charm_name]


@pytest.fixture
def units(application):
    return application.units


@pytest.fixture
def worker_units(charmed_kubernetes):
    return charmed_kubernetes.model.applications["kubernetes-worker"].units


@pytest.fixture
def deployment(kubernetes):
    with open("nginx_deployment.yaml") as f:
        for obj in codecs.load_all_yaml(f):
            # Server side apply requires an explicit namespace be passed in
            kubernetes.apply(obj, namespace=kubernetes.namespace)
    yield
    for obj in codecs.load_all_yaml(f):
        kubernetes.delete(obj, obj.metadata.name, namespace=kubernetes.namespace)


@pytest.fixture
def scaled_up_deployment(kubernetes, deployment):
    dep_obj = Deployment.Scale(
        metadata=ObjectMeta(name="nginx", namespace=kubernetes.namespace),
        spec=ScaleSpec(replicas=200),
    )
    log.info("Scaling nginx deployment up to 200 units...")
    kubernetes.replace(dep_obj, "nginx", namespace=kubernetes.namespace)


@pytest.fixture
def scaled_down_deployment(kubernetes, deployment):
    dep_obj = Deployment.Scale(
        metadata=ObjectMeta(name="nginx", namespace=kubernetes.namespace),
        spec=ScaleSpec(replicas=0),
    )
    log.info("Scaling nginx deployment down to 0 units...")
    kubernetes.replace(dep_obj, "nginx", namespace=kubernetes.namespace)
