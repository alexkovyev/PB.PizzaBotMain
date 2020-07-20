# -*- coding: utf-8 -*-

"""
Логгер заменяющий нормальный при тестировании
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from enum import Enum
from typing import NoReturn
from unittest import TestCase

from ..logger import CustomLogger


class LogLvl(Enum):
    """ Возможные уровни сообщения логгера """
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


class LogForTesting(CustomLogger):
    """ Имитирует работу логгера
    и проверяет сообщения на соответствие ожиданиям
    """
    def __init__(self, case: TestCase,
                 name: str = None, chk: bool = True):
        """Создаёт объект класса LogForTesting

        Параметры:
            case: Группа тестов, которая испльзует логгер
            name: Имя логгера для вывода в консоль (None без вывода)
            chk: Проверять ли сообщения
        """
        self.case = case
        self.wait = []
        self.print = name is not None
        self.chk = chk
        if name is not None:
            CustomLogger.__init__(self, name)

    def add_wait(self, lvl: LogLvl, msg: str, temp: bool = False) -> NoReturn:
        """Добавить в список ожидаемое сообщение

        Параметры:
            lvl: Уровень сообщения (LogLvl)
            msg: Ожидаемое сообщение
        """
        if (lvl, msg, True) not in self.wait:
            self.wait.append((lvl, msg, temp))

    def check(self, lvl: LogLvl, msg: str) -> NoReturn:
        """Проверить сообщение на ожидаемость

        Параметры:
            lvl: Уровень сообщения (LogLvl)
            msg: Проверяемое сообщение
        """
        if self.chk:
            key = -1
            for i, e in enumerate(self.wait):
                if e[:-1] == (lvl, msg):
                    key = i
                    break
            self.case.assertGreaterEqual(key, 0,
                                         f'Сообщение не ожидалось: {msg}')
            if not self.wait[key][-1]:
                self.wait.pop(key)

    def debug(self, msg: str) -> NoReturn:
        """Проверить сообщение уровня LogLvl.DEBUG

        Параметры:
            msg: Проверяемое сообщение
        """
        self.check(LogLvl.DEBUG, msg)
        if self.print:
            super().debug(msg)

    def info(self, msg: str) -> NoReturn:
        """Проверить сообщение уровня LogLvl.INFO

        Параметры:
            msg: Проверяемое сообщение
        """
        self.check(LogLvl.INFO, msg)
        if self.print:
            super().info(msg)

    def warning(self, msg: str) -> NoReturn:
        """Проверить сообщение уровня LogLvl.WARNING

        Параметры:
            msg: Проверяемое сообщение
        """
        self.check(LogLvl.WARNING, msg)
        if self.print:
            super().warning(msg)

    def error(self, msg: str) -> NoReturn:
        """Проверить сообщение уровня LogLvl.ERROR

        Параметры:
            msg: Проверяемое сообщение
        """
        self.check(LogLvl.ERROR, msg)
        if self.print:
            super().error(msg)

    def end(self) -> NoReturn:
        """ Проверить неполученные сообщения """
        for i, _ in enumerate(self.wait):
            if self.wait[i][-1]:
                self.wait.pop(i)
        self.case.assertLessEqual(
            len(self.wait), 0,
            f"Не все ожидаемые сообщения найдены: {self.wait}"
        )
        self.wait.clear()

    def close(self) -> NoReturn:
        """ Подготовить лог к декструкции """
        if self.print:
            super().close()
