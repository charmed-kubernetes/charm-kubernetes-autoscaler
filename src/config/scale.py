import logging
import collections
from types import SimpleNamespace
import yaml

from errors import JujuConfigError
from config.base import JujuBase
from config.uuid import JujuUUID


logger = logging.getLogger(__name__)
ERROR = "juju_scale invalid:"


def _juju_scale_model_uuid(model, full_cfg):
    try:
        return JujuUUID("model", model)
    except JujuConfigError:
        raise JujuConfigError(f"{ERROR} Invalid model part in '{full_cfg}'")


class JujuScale(JujuBase):
    @staticmethod
    def str_parser(to_parse):
        by_colons = to_parse.split(":")
        len_by_colons = len(by_colons)
        if len_by_colons < 3:
            raise JujuConfigError(
                f"{ERROR} Must contain at least 3 parts <min>:<max>:<application> '{to_parse}'"
            )
        elif len_by_colons == 3:
            (_min, _max, app), model = by_colons, None
        elif len_by_colons == 4:
            _min, _max, model, app = by_colons
            model = _juju_scale_model_uuid(model, to_parse)
        else:
            raise JujuConfigError(
                f"{ERROR} Must contain 4 parts <min>:<max>:<model>:<application> '{to_parse}'"
            )
        try:
            _min, _max = int(_min), int(_max)
        except ValueError:
            _min, _max = -1, -1
        if _min < 0 or _max < 0:
            raise JujuConfigError(
                f"{ERROR} <min> & <max> must be non-negative integers '{to_parse}'"
            )
        if _max <= _min:
            raise JujuConfigError(f"{ERROR} <min> should be less than <max> '{to_parse}'")
        return SimpleNamespace(min=_min, max=_max, model=model, application=app)

    @staticmethod
    def dict_parser(to_parse):
        try:
            _min = to_parse["min"]
            _max = to_parse["max"]
            app = to_parse["application"]
        except KeyError as e:
            raise JujuConfigError(f"{ERROR} missing required element {str(e)}")
        model = to_parse.get("model")
        model = _juju_scale_model_uuid(model, to_parse) if model else None
        return SimpleNamespace(min=_min, max=_max, model=model, application=app)

    def parser(self, cfg):
        if isinstance(cfg, str):
            return self.str_parser(cfg)
        elif isinstance(cfg, collections.Mapping):
            return self.dict_parser(cfg)
        raise JujuConfigError(f"{ERROR} Unexpected yaml collection type")

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
            raise JujuConfigError(f"{ERROR} not yaml or json format") from e

        if scale is None:
            self.scale = []
            return
        elif isinstance(scale, str):
            # yaml that isn't specifically a list of things -- but instead was still a string
            # this COULD be a comma separated list of parts
            scale = [part for part in scale.split(",") if part]
        elif not isinstance(scale, list):
            # yaml that was valid yaml, but not a list of things
            raise JujuConfigError(f"{ERROR} yaml or json format - expected a list")

        try:
            self.scale = [self.parser(parts) for parts in scale]
        except JujuConfigError:
            logger.error("invalid juju_scale configuration: %s", cfg)
            raise
