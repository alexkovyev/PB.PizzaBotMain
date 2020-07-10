# -*- coding: utf-8 -*-

"""
Содержит класс сообщений логгера главных файлов модуля ControllersAPI
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from .base_template import LogTemplates


class CAPIT(LogTemplates):
    """ Сообщения логгера главных файлов модуля Controllers API """
    UNSUP_PLAT = 'Unsupported platform!'
    OPEN_PORTS = 'Open ports: {ports}'
    PORTS_UNLOCKED = 'All "tty" unlocked!'
    UNLOCK_NOT_ALLOWED = 'Port unlocking not allowed!'
    HAS_NO_OPEN_PORTS = 'There is 0 open serial ports!'
    SENDING_TO_BUS = 'Sending to the bus: {cmd}'
    SENT = 'Sent'
    UNIT_DIDNT_RESPONSE = 'Unit {} isn\'t responding!'
