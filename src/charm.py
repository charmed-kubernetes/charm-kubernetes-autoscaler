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

logger = logging.getLogger(__name__)


class JujuEnvironmentError(Exception):
    pass


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
            "juju_api_endpoint",
            "juju_ca_cert",
            "juju_username",
            "juju_refresh_interval",
            "juju_model_uuid",
            "juju_application",
        ]
        self._stored.set_default(juju_api_endpoint=None)
        self._stored.set_default(juju_ca_cert=None)
        self._stored.set_default(juju_username=None)
        self._stored.set_default(juju_password=None)
        self._stored.set_default(juju_refresh_interval=5)
        self._stored.set_default(juju_model_uuid=None)
        self._stored.set_default(juju_application=None)

    def _on_juju_autoscaler_pebble_ready(self, event):
        """Define and start a workload using the Pebble API."""
        # Get a reference the container attribute on the PebbleReadyEvent
        container = event.workload
        try:
            self._evaluate_environment(container)
        except JujuEnvironmentError as e:
            self.unit.status = BlockedStatus(str(e))
            return

    def _on_config_changed(self, _):
        reevaluate = False
        juju_config_pairs = (
            (opt, getattr(self._stored, opt), self.config.get(opt)) for opt in self._juju_config
        )
        juju_changes = {
            opt: current
            for opt, stored, current in juju_config_pairs
            if stored != current and current is not None
        }
        if juju_changes:
            reevaluate = True
            logger.debug("found new juju settings: %s", ",".join(juju_changes))
            for opt, current in juju_changes.items():
                setattr(self._stored, opt, current)

        if not reevaluate:
            return

        try:
            self._evaluate_environment(self.model.unit.get_container("juju-autoscaler"))
        except JujuEnvironmentError as e:
            self.unit.status = BlockedStatus(str(e))
            return

    def _juju_environment(self):
        environment = {env: self.model.config.get(env) for env in self._juju_config}
        missing_environment = {env for env, val in environment.items() if val is None}
        if missing_environment:
            logger.debug("Missing juju-* config : %s", ",".join(missing_environment))
            raise JujuEnvironmentError("Waiting for Juju Configuration")
        return environment

    def _evaluate_environment(self, container):
        environment = self._juju_environment()

        # Define an initial Pebble layer configuration
        pebble_layer = {
            "summary": "juju-autoscaler layer",
            "description": "pebble config layer for juju-autoscaler",
            "services": {
                "juju-autoscaler": {
                    "override": "replace",
                    "summary": "juju-autoscaler",
                    "command": "gunicorn -b 0.0.0.0:80 httpbin:app -k gevent",
                    "startup": "enabled",
                    "environment": environment,
                }
            },
        }
        # Add initial Pebble config layer using the Pebble API
        container.add_layer("juju-autoscaler", pebble_layer, combine=True)
        # Autostart any services that were defined with startup: enabled
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
