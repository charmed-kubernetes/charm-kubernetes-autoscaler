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

    def __getitem__(self, item):
        _type, _default = self._types[item]
        return _type(self._stored.juju_config[item])

    def __setitem__(self, item, value):
        _type, _default = self._types[item]
        self._stored.juju_config[item] = type(_default)(value)
        return value

    def validate(self, item, potential):
        _type, _default = self._types[item]
        self[item] = _type(potential)


__all__ = ["JujuStoredState"]
