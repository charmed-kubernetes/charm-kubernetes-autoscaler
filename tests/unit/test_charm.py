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


def test_config_changed(harness):
    last_config_idx = len(harness.charm._juju_config) - 1
    for idx, opt in enumerate(harness.charm._juju_config):
        default = 5 if opt == "juju_refresh_interval" else None
        assert getattr(harness.charm._stored, opt) is default
        harness.update_config({opt: f"foo-{idx}"})
        assert getattr(harness.charm._stored, opt) == f"foo-{idx}"
        if idx != last_config_idx:
            assert harness.model.unit.status == BlockedStatus("Waiting for Juju Configuration")
    assert harness.model.unit.status == ActiveStatus("Ready to Scale")


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
