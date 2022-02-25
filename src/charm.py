#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
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
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from autoscaler import AutoScaler
from config import JujuConfig
from errors import JujuConfigError, JujuEnvironmentError
from manifests import Manifests

logger = logging.getLogger(__name__)


class KubernetesAutoscalerCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()
    CONTAINER = "juju-autoscaler"

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.install, self._install_or_upgrade)
        self.framework.observe(self.on.upgrade_charm, self._install_or_upgrade)
        self.framework.observe(self.on.juju_autoscaler_pebble_ready, self._install_or_upgrade)
        self.framework.observe(self.on.config_changed, self._install_or_upgrade)
        self.framework.observe(self.on.leader_elected, self._set_version)
        self.framework.observe(self.on.stop, self._cleanup)
        self._juju_config = JujuConfig(self._stored)

    def _install_or_upgrade(self, _event):
        autoscaler = AutoScaler()

        try:
            self._juju_config.load(self)
            autoscaler.apply_juju(self._juju_config, self)
        except (JujuConfigError, JujuEnvironmentError) as e:
            self.unit.status = BlockedStatus(str(e))
            return

        container = self.model.unit.get_container(self.CONTAINER)
        if not container or not container.can_connect():
            self.unit.status = WaitingStatus("Container Not Ready")
            return

        path, file = autoscaler.binary.parent, autoscaler.binary.name
        executable = container.list_files(path, pattern=file + "*")
        if not executable:
            self.unit.status = BlockedStatus(f"Image missing executable: {autoscaler.binary}")
            return

        container.add_layer(self.CONTAINER, autoscaler.layer, combine=True)
        container.push(*autoscaler.accounts_file, make_dirs=True, **autoscaler.root_owned)
        container.push(*autoscaler.controller_file, make_dirs=True, **autoscaler.root_owned)

        manifests = Manifests(self)
        manifests.apply_manifests()

        container.autostart()
        self.unit.status = ActiveStatus()

    def _set_version(self, _event=None):
        if self.unit.is_leader():
            self.unit.set_workload_version("Ready to Scale")

    def _cleanup(self, _):
        self.unit.status = WaitingStatus("Shutting down")
        manifests = Manifests(self)
        manifests.delete_manifest(ignore_unauthorized=True)


if __name__ == "__main__":
    main(KubernetesAutoscalerCharm)
