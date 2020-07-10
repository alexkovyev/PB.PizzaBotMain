# -*- coding: utf-8 -*-

"""
Эмулятор работы COM-порта для проведения тестирования
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from typing import NoReturn, Callable, Awaitable, Union, List
from aioserial import AioSerial
from asyncio import sleep


class PortEmulator(AioSerial):
    """Эмулирует работу COM-порта
    Читает полученное сообщение и возвращает через некоторое время
    (эмулирует задержку)
    """
    def __init__(self, handler: Callable[[bytes], Awaitable[bytes]] = None,
                 read_time: Union[float, List[float]] = 0.001):
        """Конструктор

        Параметры:
            handler: функция, выполняющаяся при появлении нового сообщения
            read_time: Время ожидания перед возвращением команды
        """
        self.handler = handler
        self.read_time = read_time

    async def write_async(self, msg: bytes) -> NoReturn:
        """Обрабатывает сообщение и записывает ответ в буффер

        Параметры:
            msg: Отправляемая команда
        """
        self.buffer = await self.handler(msg)

    def _get_sleep_time(self) -> float:
        """Возвращает длительность ожидания перед отправкой ответа

        Возврат: длительность ожидания
        """
        ret = self.read_time
        if type(ret) in (list, tuple):
            if not hasattr(self, 'index'):
                self.index = 0
            ret = ret[self.index]
            self.index += 1
            if self.index >= len(self.read_time):
                self.index = 0
        return ret

    async def read_until_async(self, sep) -> bytes:
        """Возвращает команду из буффера с задержкой

        Параметры:
            sep: Разделитель

        Возврат: Комманда из буффера
        """
        await sleep(self._get_sleep_time())
        return self.buffer
