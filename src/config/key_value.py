import logging
import yaml

from errors import ConfigError
from config.base import ConfigBase

logger = logging.getLogger(__name__)


class KeyValue(ConfigBase):
    def _validate(self, key, val):
        def t_name(y):
            return type(y).__name__

        pod_types = (str, int, bool)
        # Keys must be string-typed
        if not isinstance(key, str):
            raise ConfigError(f"{self.ERROR} Expected key to be a str -- {key} ({t_name(key)})")
        # Values must be a pod-type or list of pod-types
        elif not isinstance(val, (list, *pod_types)):
            raise ConfigError(f"{self.ERROR} Unexpected type for val -- {val} ({t_name(val)})")

        if isinstance(val, pod_types):
            # Normalize values into a list of pod_types
            val = [val]

        for item in val:
            if not isinstance(item, pod_types):
                raise ConfigError(
                    f"{self.ERROR} Unexpected type for item in val list"
                    f" -- {item} ({t_name(item)})"
                )
        return [(key, item) for item in val]

    def __init__(self, config_id, cfg):
        super().__init__(cfg)
        self.ERROR = f"{config_id} invalid:"
        try:
            key_values = yaml.safe_load(cfg.strip())
        except yaml.YAMLError as e:
            logger.error(f"invalid {config_id} configuration: %s", cfg)
            raise ConfigError(f"{self.ERROR} not yaml or json format") from e

        if key_values is None:
            self.key_values = []
            return
        elif not isinstance(key_values, dict):
            # yaml that was valid yaml, but not a list of things
            logger.error(f"invalid {config_id} configuration: %s", cfg)
            raise ConfigError(f"{self.ERROR} yaml or json format - expected a mapping")

        self.key_values = [pair for k, v in key_values.items() for pair in self._validate(k, v)]
