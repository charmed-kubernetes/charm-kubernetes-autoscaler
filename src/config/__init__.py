from config.scale import JujuScale
from config.controller import JujuController
from config.ca_cert import JujuCaCert
from config.model import JujuModel


class JujuStoredState:
    _types = {
        "api_endpoints": (JujuController, ""),
        "ca_cert": (JujuCaCert, ""),
        "username": (str, ""),
        "password": (str, ""),
        "refresh_interval": (int, 5),
        "model_uuid": (JujuModel, ""),
        "scale": (JujuScale, ""),
    }

    def __init__(self, storage):
        self._stored = storage
        self._stored.set_default(
            juju_config={key: _default for key, (_type, _default) in self._types.items()}
        )
        self._cached = {}

    def __getitem__(self, item):
        if item not in self._types:
            raise KeyError(item)

        try:
            value = self._cached[item]
        except KeyError:
            _type, _default = self._types[item]
            value = _type(self._stored.juju_config[item])
            self._cached[item] = value
        return value

    def __setitem__(self, item, value):
        _type, _default = self._types[item]
        if isinstance(value, _type):
            self._cached[item] = value
            self._stored.juju_config[item] = type(_default)(value)
        elif isinstance(value, type(_default)):
            self._cached[item] = _type(value)
            self._stored.juju_config[item] = value
        else:
            raise TypeError(f"value {value} must be of type {'or '.join([_type, type(_default)])}")

        return value

    def validate(self, item, potential):
        _type, _default = self._types[item]
        self[item] = _type(potential)


__all__ = ["JujuStoredState"]
