from dataclasses import dataclass, field
import logging
from pathlib import Path
import sys

if sys.version_info >= (3, 8):
    from typing import TypedDict, List, Tuple
else:
    from typing_extensions import TypedDict
    from typing import List, Tuple
import yaml

from errors import JujuEnvironmentError

logger = logging.getLogger(__name__)
CONTROLLER = "scaler-controller"
CLOUD_CONFIG_FILE = Path("/", "config", "cloud-config.yaml")


CloudConfig = TypedDict(
    "CloudConfig", {"endpoints": List[str], "ca-cert": str, "user": str, "password": str}
)


@dataclass
class AutoScaler:
    cloud_config: CloudConfig = field(default_factory=CloudConfig)
    command: str = ""

    def _build_command(self, config, charm):
        model, scale = config["default_model_uuid"], config["scale"]
        node_groups = scale.nodes(default_model=model.cfg)
        if not node_groups:
            logger.info("Missing juju-scale config")
            raise JujuEnvironmentError("Waiting for Juju Configuration")

        namespace = f"--namespace {charm.model.name.strip()}"
        provider = f"--cloud-provider=juju --cloud-config={CLOUD_CONFIG_FILE}"
        nodes = " ".join([f"--nodes {node}" for node in node_groups])

        extra_args = config["extra_args"].key_values
        extra = ""
        if extra_args:
            extra = " " + " ".join(sorted(f"--{key}='{value}'" for key, value in extra_args))

        self.command = f"{self.binary} {namespace} {provider} {nodes}{extra}"
        return self

    def apply(self, config, charm):
        self._build_command(config, charm)

        self.cloud_config = {
            "ca-cert": config["ca_cert"].decoded,
            "endpoints": config["api_endpoints"].endpoints,
            "user": config["username"],
            "password": config["password"],
        }

        missing = {env for env, val in self.cloud_config.items() if not val}
        if missing:
            logger.info("Missing cloud-config : %s", ",".join(missing))
            raise JujuEnvironmentError(f"Waiting for Juju Configuration: {','.join(missing)}")
        return self

    def authorize(self, container):
        container.add_layer(container.name, self.layer, combine=True)
        container.push(*self.cloud_config_file, make_dirs=True, **self.root_owned)

    @property
    def layer(self):
        logger.info("starting autoscaler with command %s", self.command)
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
    def root_owned(self):
        return dict(permissions=0o600, user_id=0, group_id=0)

    @property
    def cloud_config_file(self) -> Tuple[str, str]:
        return str(CLOUD_CONFIG_FILE), yaml.safe_dump(self.cloud_config)
