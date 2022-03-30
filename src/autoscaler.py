import uuid
from dataclasses import dataclass, field
import logging
from ops.pebble import ExecError
from pathlib import Path
from typing import TypedDict
import yaml

from errors import JujuEnvironmentError

logger = logging.getLogger(__name__)
CONTROLLER = "scaler-controller"
CLOUD_CONFIG_FILE = Path("/", "config", "cloud-config.yaml")


ControllerData = TypedDict(
    "ControllerData",
    {"api-endpoints": list[str], "uuid": str, "ca-cert": str},
)
Secrets = TypedDict("Secrets", {"user": str, "password": str})
ModelData = TypedDict("ModelData", {"models": dict, "current-model": str})
CloudConfig = TypedDict(
    "CloudConfig", {"endpoints": list[str], "ca-cert": str, "user": str, "password": str}
)


@dataclass
class AutoScaler:
    controller_data: ControllerData = field(default_factory=ControllerData)
    model_data: ModelData = field(default_factory=ModelData)
    secrets: Secrets = field(default_factory=Secrets)
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

        self.secrets = {
            "user": config["username"],
            "password": config["password"],
        }

        self.controller_data = {
            "api-endpoints": config["api_endpoints"].endpoints,
            "uuid": str(uuid.uuid4()),  # juju CLI requires a random unique uuid
            "ca-cert": config["ca_cert"].decoded,
        }

        default_model_uuid = config["default_model_uuid"].cfg
        if default_model_uuid:
            self.model_data = {
                "models": {"admin/controller": {}, "admin/default": {"uuid": default_model_uuid}},
                "current-model": "admin/default",
            }
        else:
            self.model_data = {
                "models": {"admin/controller": {}},
                "current-model": "admin/controller",
            }

        missing = {env for env, val in {**self.controller_data, **self.secrets}.items() if not val}
        if missing:
            logger.info("Missing config : %s", ",".join(missing))
            raise JujuEnvironmentError(f"Waiting for Juju Configuration: {','.join(missing)}")
        return self

    def authorize(self, container):
        container.add_layer(container.name, self.layer, combine=True)
        container.push(*self.accounts_file, make_dirs=True, **self.root_owned)
        container.push(*self.controller_file, make_dirs=True, **self.root_owned)
        container.push(*self.models_file, make_dirs=True, **self.root_owned)
        container.push(*self.cloud_config_file, make_dirs=True, **self.root_owned)
        self._authorize_juju_cli(container)

    @staticmethod
    def _authorize_juju_cli(container):
        symlink_juju = ["ln", "-s", "/juju", "/bin/juju"]
        process = container.exec(symlink_juju)  # create a symlink at /bin/juju
        try:
            stdout, _ = process.wait_output()
        except ExecError as e:
            if "'/bin/juju': File exists" not in e.stderr:
                logger.error("Exited with code %d. Stderr:", e.exit_code)
                for line in e.stderr.splitlines():
                    logger.error("    %s", line)

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
    def accounts(self):
        return {
            "controllers": {
                CONTROLLER: {
                    **self.secrets,
                    "last-known-access": "superuser",
                }
            }
        }

    @property
    def accounts_file(self):
        return "/root/.local/share/juju/accounts.yaml", yaml.safe_dump(self.accounts)

    @property
    def root_owned(self):
        return dict(permissions=0o600, user_id=0, group_id=0)

    @property
    def controllers(self):
        return {
            "controllers": {CONTROLLER: {**self.controller_data}},
            "current-controller": CONTROLLER,
        }

    @property
    def controller_file(self):
        return "/root/.local/share/juju/controllers.yaml", yaml.safe_dump(self.controllers)

    @property
    def models(self):
        return {
            "controllers": {CONTROLLER: {**self.model_data}},
        }

    @property
    def models_file(self):
        return "/root/.local/share/juju/models.yaml", yaml.safe_dump(self.models)

    @property
    def cloud_config(self) -> CloudConfig:
        return {
            "ca-cert": self.controller_data["ca-cert"],
            "endpoints": self.controller_data["api-endpoints"],
            "user": self.secrets["user"],
            "password": self.secrets["password"],
        }

    @property
    def cloud_config_file(self) -> tuple[str, str]:
        return str(CLOUD_CONFIG_FILE), yaml.safe_dump(self.cloud_config)
