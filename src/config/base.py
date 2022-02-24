from dataclasses import dataclass


@dataclass
class JujuBase:
    cfg: str

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.cfg
        elif isinstance(other, type(self)):
            return other.cfg == self.cfg
        return False

    def __str__(self):
        return self.cfg
