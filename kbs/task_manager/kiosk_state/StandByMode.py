"""Это описание метода Stand_by
не доделано
"""

from .BaseMode import BaseMode
from kbs.data.kiosk_modes.kiosk_modes import KioskModeNames


class StandBy(BaseMode):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return str(KioskModeNames.STANDBYMODE)
