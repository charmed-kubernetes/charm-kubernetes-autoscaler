from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Dict
import yaml

from errors import JujuEnvironmentError

logger = logging.getLogger(__name__)


@dataclass
class AutoScaler:
    controller_data: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    command: str = ""

    def _build_command(self, juju_config, charm):
        model, scale = juju_config["default_model_uuid"], juju_config["scale"]
        node_groups = scale.nodes(default_model=model.cfg)
        if not node_groups:
            logger.info("Missing juju-scale config")
            raise JujuEnvironmentError("Waiting for Juju Configuration")

        nodes_args = " ".join([f"--nodes {node}" for node in node_groups])
        namespace_args = f"--namespace {charm.model.name.strip()}"

        self.command = f"{self.binary} {nodes_args} {namespace_args}"
        return self

    def apply_juju(self, juju_config, charm):
        self._build_command(juju_config, charm)
        self.secrets = {
            "user": juju_config["username"],
            "password": juju_config["password"],
        }
        self.controller_data = {
            "api-endpoints": juju_config["api_endpoints"].endpoints,
            "uuid": juju_config["controller_uuid"].cfg,
            "ca-cert": juju_config["ca_cert"].decoded,
        }
        missing = {env for env, val in {**self.controller_data, **self.secrets}.items() if not val}
        if missing:
            logger.info("Missing config : %s", ",".join(missing))
            raise JujuEnvironmentError(f"Waiting for Juju Configuration: {','.join(missing)}")

        return self

    @property
    def layer(self):
        return {
            "summary": "juju-autoscaler layer",
            "description": "pebble config layer for juju-autoscaler",
            "services": {
                "juju-autoscaler": {
                    "override": "replace",
                    "summary": "juju-autoscaler",
                    "command": self.command,
                    "startup": "enabled",
                }
            },
        }

    @property
    def binary(self):
        return Path("/", "cluster-autoscaler")

    @property
    def accounts(self):
        return {
            "controllers": {
                "scaler-controller": {
                    **self.secrets,
                    "last-known-access": "superuser",
                }
            }
        }

    @property
    def accounts_file(self):
        return "/root/.local/share/juju/accounts.yaml", yaml.safe_dump(self.accounts)

    @property
    def accounts_permissions(self):
        return dict(permissions=0o600, user_id=0, group_id=0)

    @property
    def controllers(self):
        return {"controllers": {"scaler-controller": {**self.controller_data}}}

    @property
    def controllers_file(self):
        return "/root/.local/share/juju/controllers.yaml", yaml.safe_dump(self.controllers)

    @property
    def controllers_permissions(self):
        return dict(permissions=0o600, user_id=0, group_id=0)
