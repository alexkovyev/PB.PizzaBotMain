# -*- coding: utf-8 -*-

"""
Cодержит класс сообщений логируемых событий диспетчера узлов
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from .base_template import LogTemplates


class UDT(LogTemplates):
    """ Сообщения лога диспетчера событий узлов """
    EVENT_EMIT = 'Узлом вызвано событие: {}'
