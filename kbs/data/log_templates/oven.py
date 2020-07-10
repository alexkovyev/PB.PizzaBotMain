# -*- coding: utf-8 -*-

"""
Содержит класс сообщений логгера класса узла нарезки
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from .unit import UT


class OT(UT):
    """ Сообщения логгера класса узла печи """
    BAKE_DONE = 'Oven: bake has been done!'
    BAKE_ERR = 'Oven: error occurred, bake hasn\'t been done'
