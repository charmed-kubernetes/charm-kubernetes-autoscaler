import logging
import os
from errors import JujuConfigError
from config.base import JujuBase

logger = logging.getLogger(__name__)


class JujuController(JujuBase):
    @staticmethod
    def invalid(address_port):
        if len(address_port) != 2:
            return f"Must contain 2 parts <address>:<port> -- {address_port}"
        address, port = address_port
        try:
            port = int(port)
        except ValueError:
            port = -1
        if not 0 < port < 65535:
            return f"tcp port is out of bounds -- {address_port}"

    def __init__(self, cfg):
        super().__init__(cfg)
        if cfg == "":
            cfg = os.environ.get("JUJU_API_ADDRESSES") or ""
        if cfg.strip() != "":
            connections = [parts.strip().split(":") for parts in cfg.split(",") if parts]
            failures = [fails for fails in map(self.invalid, connections) if fails]
            if failures:
                logger.error("invalid juju_api_endpoints configuration: %s", ", ".join(failures))
                raise JujuConfigError("juju_api_endpoints invalid")
