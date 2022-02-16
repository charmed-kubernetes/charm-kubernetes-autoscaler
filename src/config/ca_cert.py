import binascii
import logging
import base64
from errors import JujuConfigError

logger = logging.getLogger(__name__)


class JujuCaCert:
    @classmethod
    def parse(cls, cfg):
        if cfg.strip() == "":
            return cls("", cfg)
        try:
            decoded = base64.b64decode(cfg)
        except binascii.Error as err:
            logger.exception("invalid juju_ca_cert configuration: %s", err)
            return JujuConfigError("juju_ca_cert invalid")
        return cls(decoded, cfg)

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.cfg
        elif isinstance(other, JujuCaCert):
            return other.cfg == self.cfg
        return False

    def __init__(self, decoded, cfg):
        self.decoded = decoded
        self.cfg = cfg
