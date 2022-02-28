import logging
import yaml

from errors import ConfigError
from config.base import ConfigBase

logger = logging.getLogger(__name__)


class KeyValue(ConfigBase):
    def validate(self, key, val):
        def t_name(y):
            return type(y).__name__

        if not isinstance(key, str):
            raise ConfigError(f"{self.ERROR} Expected key to be a str -- {key} ({t_name(key)})")
        elif not isinstance(val, str):
            raise ConfigError(f"{self.ERROR} Expected val to be a str -- {val} ({t_name(val)})")
        return key, val

    def __init__(self, config_id, cfg):
        super().__init__(cfg)
        self.ERROR = f"{config_id} invalid:"
        try:
            key_values = yaml.safe_load(cfg.strip())
        except yaml.YAMLError as e:
            logger.error(f"invalid {config_id} configuration: %s", cfg)
            raise ConfigError(f"{self.ERROR} not yaml or json format") from e

        if key_values is None:
            self.key_values = {}
            return
        elif not isinstance(key_values, dict):
            # yaml that was valid yaml, but not a list of things
            logger.error(f"invalid {config_id} configuration: %s", cfg)
            raise ConfigError(f"{self.ERROR} yaml or json format - expected a mapping")

        self.key_values = dict(self.validate(k, v) for k, v in key_values.items())
