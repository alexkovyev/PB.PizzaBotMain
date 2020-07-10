# -*- coding: utf-8 -*-

"""
Класс эмулятор работы физической шины для тестов
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from typing import NoReturn, Union, List

from .unit_emu import UnitEmulator


class BusEmulator:
    """ Эмулирует работу физической шины """
    def __init__(self, loop,
                 unit: Union[UnitEmulator, List[UnitEmulator]] = None):
        """ Инициализирует класс эмулятора шины

        Параметры:
            loop: Запущенный цикл asyncio
            unit: Один или несколько узлов подключенных к шине
        """
        self.units = []
        self.loop = loop
        if unit is not None:
            self.add_unit(unit)

    def set_state(self, addr: int, state: int) -> NoReturn:
        """Изменяет состояние узла с заданным адресом

        Параметры:
            addr: Адрес узла
            state: Новое состояние
        """
        for u in self.units:
            if u.addr == addr:
                u.state = state
                return

    def add_unit(self,
                 unit: Union[UnitEmulator, List[UnitEmulator]]) -> NoReturn:
        """Добавляет новый узел в шину

        Параметры:
            unit: Один или несколько новых узлов
        """
        if type(unit) in (list, tuple):
            self.units.extend(unit)
        else:
            self.units.append(unit)

    async def execute(self, cmd: bytes) -> bytes:
        """Эмулирует отправку пришедшей команды на все узлы

        Параметры:
            cmd: байт-строка команда

        Возврат: байт-строка ответ
        """
        future = self.loop.create_future()
        for u in self.units:
            self.loop.create_task(u.execute(cmd, future))
        await future
        return future.result()
