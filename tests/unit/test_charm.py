# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml


from charm import KubernetesAutoscalerCharm
from ops.model import ActiveStatus, BlockedStatus, ModelError
from ops.testing import Harness


@pytest.fixture(scope="function")
def harness(request):
    harness = Harness(KubernetesAutoscalerCharm)
    harness.begin()
    harness._backend.model_name = request.node.originalname
    yield harness
    harness.cleanup()


@pytest.mark.parametrize(
    "opt, valid, invalid",
    [
        (
            "api_endpoints",
            "1.2.3.4:17070, 1.2.3.4:17070, 1.2.3.4:17070",
            "1.2.3.4:70000,",
        ),
        ("ca_cert", "dGVzdA==", "*testing*"),  # "test" base64 encoded
        (
            "username",
            "alice",
            "",
        ),
        ("password", "secret", ""),
        ("default_model_uuid", "cdcaed9f-336d-47d3-83ba-d9ea9047b18c", "nope"),
        (
            "scale",
            "- {min: 0, max: 1, application: kubernetes-worker}",
            "- {min: 1, max: 0, application: kubernetes-worker}",
        ),
    ],
)
def test_config_changed_individually(opt, valid, invalid, harness):
    default = ""
    assert harness.charm._stored.juju_config.get(opt) == default

    harness.update_config({f"juju_{opt}": valid})
    assert harness.charm._stored.juju_config.get(opt) == valid
    assert harness.model.unit.status == BlockedStatus("Waiting for Juju Configuration")

    if invalid:
        harness.update_config({f"juju_{opt}": invalid})
        assert harness.charm._stored.juju_config.get(opt) == valid
        assert harness.model.unit.status.message.startswith(f"juju_{opt} invalid")

    harness.update_config({f"juju_{opt}": default})
    assert harness.charm._stored.juju_config.get(opt) == default


def test_juju_autoscaler_pebble_ready_initial_plan(harness):
    # Check the initial Pebble plan is empty
    initial_plan = harness.get_container_pebble_plan("juju-autoscaler")
    assert initial_plan.to_yaml() == "{}\n"


def test_juju_autoscaler_pebble_ready_before_config(harness):
    # Check the initial Pebble plan is empty
    initial_plan = harness.get_container_pebble_plan("juju-autoscaler")
    assert initial_plan.to_yaml() == "{}\n"
    # Expected plan after Pebble ready with default config
    expected_plan = {}
    # Get the juju-autoscaler container from the model
    container = harness.model.unit.get_container("juju-autoscaler")
    # Emit the PebbleReadyEvent carrying the juju-autoscaler container
    harness.charm.on.juju_autoscaler_pebble_ready.emit(container)
    # Get the plan now we've run PebbleReady
    updated_plan = harness.get_container_pebble_plan("juju-autoscaler").to_dict()
    # Check we've got the plan we expected
    assert expected_plan == updated_plan
    # Check the service was started
    with pytest.raises(ModelError):
        harness.model.unit.get_container("juju-autoscaler").get_service("juju-autoscaler")
    # Ensure we set an BlockedStatus with a reason
    assert harness.model.unit.status == BlockedStatus("Waiting for Juju Configuration")


@pytest.fixture
def mock_pebble_exec(harness):
    container = harness.model.unit.get_container("juju-autoscaler")
    prior_exec = container.pebble.exec
    container.pebble.exec = MagicMock()
    yield container, container.pebble.exec.return_value.wait_output
    container.pebble.exec = prior_exec


def test_juju_autoscaler_pebble_ready_after_config_minimal(
    lightkube_client, mock_pebble_exec, harness
):
    container, pebble_exec = mock_pebble_exec
    pebble_exec.return_value = b"", b""

    testdata = Path("tests/data/pebble_cfg_minimum/")
    container.push("/cluster-autoscaler", "#!/bin/sh")
    text = Path(testdata, "test_ca.cert").read_text().encode("ascii")
    text = base64.b64encode(text).decode("ascii")
    with patch("uuid.uuid4", return_value="511730b6-55a4-4a9e-84d7-80e46896a2d1"):
        harness.update_config(
            {
                "juju_api_endpoints": "1.2.3.4:17070",
                "juju_username": "alice",
                "juju_password": "secret",
                "juju_default_model_uuid": "cdcaed9f-336d-47d3-83ba-d9ea9047b18c",
                "juju_scale": "- {min: 0, max: 3, application: kubernetes-worker}",
                "juju_ca_cert": text,
                "autoscaler_extra_args": "{v: 5, scale-down-unneeded-time: 5m0s}",
            }
        )
    assert harness.model.unit.status == ActiveStatus()

    plan = harness.get_container_pebble_plan("juju-autoscaler")
    text = Path(testdata, "layer.yaml").read_text()
    assert plan.to_dict() == yaml.safe_load(text)

    config_path = "/config"
    files = container.list_files(config_path)
    assert [file.name for file in files] == ["cloud-config.yaml"]
    contents = yaml.safe_load(Path(testdata, "cloud-config.yaml").read_text())
    assert yaml.safe_load(container.pull(f"{config_path}/cloud-config.yaml").read()) == contents

    lightkube_client.delete.assert_called()
    lightkube_client.create.assert_called()


@patch("ops.model.Container.get_services", autospec=True)
@patch("ops.model.Container.stop", autospec=True)
def test_juju_autoscaler_stop(mock_getservices, mock_stop, harness):
    container = harness.model.unit.get_container("juju-autoscaler")
    mock_getservices.return_value = {"juju-autoscaler: []"}
    harness.charm.on.stop.emit()
    mock_stop.assert_called_once_with(container, "juju-autoscaler")
