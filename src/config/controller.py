import logging
import os
from errors import ConfigError
from config.base import ConfigBase

logger = logging.getLogger(__name__)
ERROR = "juju_api_endpoints invalid:"


class ConfigController(ConfigBase):
    @staticmethod
    def invalid(cfg):
        by_colons = cfg.split(":")
        if len(by_colons) != 2:
            raise ConfigError(f"{ERROR} Must contain 2 parts <address>:<port> -- {cfg}")
        address, port = by_colons
        try:
            port = int(port)
        except ValueError:
            port = -1
        if not 0 < port < 65535:
            raise ConfigError(f"{ERROR} tcp port is out of bounds -- {cfg}")
        return cfg

    @property
    def endpoints(self):
        if not self._endpoints:
            return os.environ.get("JUJU_API_ADDRESSES", "").split(" ")
        return self._endpoints

    def __init__(self, cfg):
        super().__init__(cfg)
        self._endpoints = []
        if cfg.strip() != "":
            self._endpoints = [self.invalid(parts.strip()) for parts in cfg.split(",") if parts]
