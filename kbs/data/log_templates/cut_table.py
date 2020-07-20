# -*- coding: utf-8 -*-

"""
Содержит класс сообщений логгера класса узла нарезки
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from .unit import UT


class CTT(UT):
    """ Сообщения логгера класса узла нарезки """
    CUT_DONE = 'CutTable: cut has been done!'
    CUT_ERR = 'CutTable: error occurred, cut hasn\'t been done'
