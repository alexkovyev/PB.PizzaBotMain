# -*- coding: utf-8 -*-

"""
Содержит класс сообщений базового класса узла
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from .base_template import LogTemplates


class UT(LogTemplates):
    """ Сообщения логгера базового класса узла """
    """ Unit Templates """
    RET_ERROR = 'Unit returns error!'
    WORK_DONE = 'Unit works done'
    ALIVE = 'Unit {} is Alive'
    NOT_ALIVE = 'Unit {} isn\'t Alive!'
    NO_RES_ERR = 'Unit {} didn\'t send response!'
    NO_RES = 'Unit {} didn\'t send response!'
    RESPONSE = 'Unit successfully respond'
    REP_ANS = 'Unit respond after {} attempts'
    REPEATING = 'Repeating command! Attempt: {}'
