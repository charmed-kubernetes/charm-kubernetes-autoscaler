import logging
import json
import collections.abc
from types import SimpleNamespace
import yaml

from errors import ConfigError
from config.base import ConfigBase
from config.uuid import ConfigUUID


logger = logging.getLogger(__name__)
ERROR = "juju_scale invalid:"


def _juju_scale_model_uuid(model, full_cfg):
    try:
        return ConfigUUID("model", model)
    except ConfigError:
        raise ConfigError(f"{ERROR} Invalid model uuid - '{full_cfg}'")


def _validate(_min, _max, app, model, cfg):
    try:
        _min, _max = int(_min), int(_max)
    except ValueError:
        _min, _max = -1, -1
    if _min <= 0 or _max <= 0:
        raise ConfigError(f"{ERROR} <min> & <max> must be non-negative, non-zero integers - '{cfg}'")
    if _max <= _min:
        raise ConfigError(f"{ERROR} <min> should be less than <max> - '{cfg}'")
    return SimpleNamespace(min=_min, max=_max, model=model, application=app)


def _parse(cfg):
    json_cfg = json.dumps(cfg)
    if not isinstance(cfg, collections.abc.Mapping):
        raise ConfigError(f"{ERROR} Unexpected yaml collection type")
    try:
        _min, _max, app = (cfg[k] for k in ["min", "max", "application"])
    except KeyError as e:
        raise ConfigError(f"{ERROR} missing required element {e} - {json_cfg}")
    model = cfg.get("model")
    model = _juju_scale_model_uuid(str(model), json_cfg) if model else None
    return _validate(_min, _max, app, model, json_cfg)


class ConfigScale(ConfigBase):
    def nodes(self, default_model=None):
        return [
            f"{part.min}:{part.max}:{part.model or default_model}:{part.application}"
            for part in self.scale
            if (part.model or default_model)
        ]

    def __init__(self, cfg):
        super().__init__(cfg)
        try:
            scale = yaml.safe_load(cfg.strip())
        except yaml.YAMLError as e:
            logger.error("invalid juju_scale configuration: %s", cfg)
            raise ConfigError(f"{ERROR} not yaml or json format") from e

        if scale is None:
            self.scale = []
            return
        elif not isinstance(scale, list):
            # yaml that was valid yaml, but not a list of things
            raise ConfigError(f"{ERROR} yaml or json format - expected a list")

        try:
            self.scale = [_parse(parts) for parts in scale]
        except ConfigError:
            logger.error("invalid juju_scale configuration: %s", cfg)
            raise
