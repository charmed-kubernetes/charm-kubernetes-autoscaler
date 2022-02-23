# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
import base64
from pathlib import Path
from unittest.mock import patch

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
            "- 0:1:kubernetes-worker",
            "- 1:0:kubernetes-worker",
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


def test_juju_autoscaler_pebble_ready_after_config_minimal(harness):
    testdata = Path("tests/data/pebble_cfg_minimum/")
    container = harness.model.unit.get_container("juju-autoscaler")
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
                "juju_scale": "- 0:3:kubernetes-worker",
                "juju_ca_cert": text,
            }
        )
    assert harness.model.unit.status == ActiveStatus()

    plan = harness.get_container_pebble_plan("juju-autoscaler")
    text = Path(testdata, "layer.yaml").read_text()
    assert plan.to_dict() == yaml.safe_load(text)

    files = container.list_files("/root/.local/share/juju")
    assert [file.name for file in files] == ["accounts.yaml", "controllers.yaml"]

    config_file = next(file for file in files if file.name == "accounts.yaml")
    assert (config_file.user_id, config_file.group_id) == (0, 0)

    accounts = yaml.safe_load(Path(testdata, "accounts.yaml").read_text())
    assert (
        yaml.safe_load(container.pull("/root/.local/share/juju/accounts.yaml").read()) == accounts
    )

    controller_file = next(file for file in files if file.name == "controllers.yaml")
    assert (controller_file.user_id, controller_file.group_id) == (0, 0)

    accounts = yaml.safe_load(Path(testdata, "controllers.yaml").read_text())
    assert (
        yaml.safe_load(container.pull("/root/.local/share/juju/controllers.yaml").read())
        == accounts
    )
