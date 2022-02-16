import logging
from errors import JujuConfigError


logger = logging.getLogger(__name__)


class JujuController:
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

    @classmethod
    def parse(cls, cfg):
        if cfg.strip() == "":
            return cls([], cfg)
        parts = [parts.strip().split(":") for parts in cfg.split(",")]
        failures = [fails for fails in map(cls.invalid, parts) if fails]
        if failures:
            logger.error("invalid juju_api_endpoints configuration: %s", ", ".join(failures))
            return JujuConfigError("juju_api_endpoints invalid")
        return cls(parts, cfg)

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.cfg
        elif isinstance(other, JujuController):
            return other.cfg == self.cfg
        return False

    def __init__(self, connections, cfg):
        self.connections = connections
        self.cfg = cfg
