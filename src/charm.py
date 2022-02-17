#!/usr/bin/env python3
# Copyright 2022 Adam Dyess
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

from errors import JujuConfigError, JujuEnvironmentError
from autoscaler import AutoScaler
from config import JujuCaCert, JujuController, JujuModel, JujuScale, validate_juju_config

logger = logging.getLogger(__name__)


class KubernetesAutoscalerCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(
            self.on.juju_autoscaler_pebble_ready, self._on_juju_autoscaler_pebble_ready
        )
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(
            self.on.refresh_controller_action, self._on_refresh_controller_action
        )

        self._juju_config = [
            key[len("juju_") :] for key in self.config.keys() if key.startswith("juju_")
        ]
        self._stored.set_default(
            juju_config={
                "api_endpoints": JujuController(""),
                "ca_cert": JujuCaCert(""),
                "username": "",
                "password": "",
                "refresh_interval": 5,
                "model_uuid": JujuModel(""),
                "scale": JujuScale(""),
            }
        )

    def _on_juju_autoscaler_pebble_ready(self, event):
        """Define and start a workload using the Pebble API."""
        # Get a reference the container attribute on the PebbleReadyEvent
        container = event.workload
        try:
            self._pebble_apply(container)
        except JujuEnvironmentError as e:
            self.unit.status = BlockedStatus(str(e))
            return

    def _on_juju_config_changed(self, _):
        juju_config_pairs = (
            (opt, self._stored.juju_config.get(opt), self.config.get(f"juju_{opt}"))
            for opt in self._juju_config
        )
        juju_changes = {
            opt: potential for opt, stored, potential in juju_config_pairs if stored != potential
        }
        if not juju_changes:
            return

        logger.info("found new juju settings: %s", ",".join(juju_changes))
        try:
            for opt, potential in juju_changes.items():
                self._stored.juju_config[opt] = validate_juju_config(opt, potential)
        except JujuConfigError as e:
            return BlockedStatus(str(e))

    def _on_config_changed(self, _):
        juju_invalid = self._on_juju_config_changed(_)
        if juju_invalid:
            self.unit.status = juju_invalid
            return

        try:
            self._pebble_apply(self.model.unit.get_container("juju-autoscaler"))
        except JujuEnvironmentError as e:
            self.unit.status = BlockedStatus(str(e))
            return

    def _pebble_apply(self, container):
        # Add initial Pebble config layer using the Pebble API
        autoscaler = AutoScaler().apply_juju(self._stored.juju_config)
        container.add_layer("juju-autoscaler", autoscaler.layer, combine=True)
        container.push(
            "/opt/autoscaler/autoscaler.conf",
            autoscaler.conf,
            permissions=0o600,
            user_id=0,
            group_id=0,
            make_dirs=True,
        )
        container.autostart()
        self.unit.status = ActiveStatus("Ready to Scale")

    def _on_refresh_controller_action(self, event):
        """Just an example to show how to receive actions."""
        fail = event.params["fail"]
        if fail:
            event.fail(fail)
        else:
            event.set_results({"fortune": "A bug in the code is worth two in the documentation."})


if __name__ == "__main__":
    main(KubernetesAutoscalerCharm)
