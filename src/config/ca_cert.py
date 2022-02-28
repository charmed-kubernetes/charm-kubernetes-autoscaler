import binascii
import logging
import base64
from errors import ConfigError
from config.base import ConfigBase

logger = logging.getLogger(__name__)


class ConfigCaCert(ConfigBase):
    def __init__(self, cfg):
        super().__init__(cfg)
        try:
            self.decoded = base64.b64decode(cfg).decode("ascii")
        except binascii.Error as err:
            logger.exception("invalid juju_ca_cert configuration: %s", err)
            raise ConfigError("juju_ca_cert invalid") from err
