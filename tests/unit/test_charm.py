# Copyright 2022 Adam Dyess
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

from unittest.mock import Mock

import pytest

from charm import KubernetesAutoscalerCharm
from ops.model import ActiveStatus, BlockedStatus, ModelError
from ops.testing import Harness


@pytest.fixture(scope="function")
def harness():
    harness = Harness(KubernetesAutoscalerCharm)
    harness.begin()
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
        ("refresh_interval", 10, ""),
        ("model_uuid", "cdcaed9f-336d-47d3-83ba-d9ea9047b18c", "nope"),
        (
            "scale",
            "0:1:kubernetes-worker",
            "1:0:kubernetes-worker",
        ),
    ],
)
def test_config_changed_individually(opt, valid, invalid, harness):
    default = 5 if opt == "refresh_interval" else ""
    assert harness.charm._stored.juju_config.get(opt) == default

    harness.update_config({f"juju_{opt}": valid})
    assert harness.charm._stored.juju_config.get(opt) == valid
    assert harness.model.unit.status == BlockedStatus("Waiting for Juju Configuration")

    if invalid:
        harness.update_config({f"juju_{opt}": invalid})
        assert harness.charm._stored.juju_config.get(opt) == valid
        assert harness.model.unit.status == BlockedStatus(f"juju_{opt} invalid")

    harness.update_config({f"juju_{opt}": default})
    assert harness.charm._stored.juju_config.get(opt) == default


def test_action(harness):
    # the harness doesn't (yet!) help much with actions themselves
    action_event = Mock(params={"fail": ""})
    harness.charm._on_refresh_controller_action(action_event)
    assert action_event.set_results.called


def test_action_fail(harness):
    action_event = Mock(params={"fail": "fail this"})
    harness.charm._on_refresh_controller_action(action_event)
    assert action_event.fail.call_args == [("fail this",)]


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
