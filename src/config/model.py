import logging
import uuid
from errors import JujuConfigError

logger = logging.getLogger(__name__)


class JujuModel:
    @classmethod
    def parse(cls, cfg):
        if cfg.strip() == "":
            return cls(None, cfg)
        try:
            decoded = uuid.UUID(cfg)
        except ValueError as err:
            logger.exception("invalid juju_model_uuid configuration: %s", err)
            return JujuConfigError("juju_model_uuid invalid")
        return cls(decoded, cfg)

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.cfg
        elif isinstance(other, JujuModel):
            return other.cfg == self.cfg
        return False

    def __init__(self, decoded, cfg):
        self.uuid = decoded
        self.cfg = cfg
