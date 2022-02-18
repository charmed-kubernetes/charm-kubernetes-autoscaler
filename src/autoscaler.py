from dataclasses import dataclass, field
import logging
from typing import Dict
import yaml

from errors import JujuEnvironmentError

logger = logging.getLogger(__name__)


@dataclass
class AutoScaler:
    environment: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    command: str = ""

    def _build_command(self, scale):
        node_groups = scale.scale
        if not node_groups:
            logger.info("Missing juju-scale config")
            raise JujuEnvironmentError("Waiting for Juju Configuration")
        else:
            args = [f"--nodes {node}" for node in node_groups]
            self.command = f"cluster-autoscaler {' '.join(args)}"
        return self

    def apply_juju(self, juju_config):
        self._build_command(juju_config["scale"])
        self.secrets = {
            "JUJU_USERNAME": juju_config["username"],
            "JUJU_PASSWORD": juju_config["password"],
        }
        self.environment = {
            "JUJU_API_ENDPOINTS": juju_config["api_endpoints"].cfg,
            "JUJU_MODEL_UUID": juju_config["model_uuid"].cfg,
        }
        missing = {env for env, val in {**self.environment, **self.secrets}.items() if not val}
        if missing:
            logger.info("Missing config : %s", ",".join(missing))
            raise JujuEnvironmentError("Waiting for Juju Configuration")

        self.environment["JUJU_CA_CERT"] = juju_config["ca_cert"].cfg
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
                    "environment": self.environment,
                }
            },
        }

    @property
    def secrets_file(self):
        return "/opt/autoscaler/autoscaler.conf", yaml.safe_dump(self.secrets)

    @property
    def secrets_permissions(self):
        return dict(permissions=0o600, user_id=0, group_id=0)
