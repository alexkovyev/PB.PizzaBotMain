# -*- coding: utf-8 -*-

"""
Класс эмулятора поведения узла для проведения тестов
"""
# Автор: Александр Сироткин aka goodmice <hamel2517@gmail.com>
# Лицензия: MIT License

from typing import NoReturn

from asyncio import Future

from ...cntrls_api.disp_cmd import DispCmd
from ...data.unit_cmds import UnitCmd


class UnitEmulator:
    """ Эмулирует поведение узла для проведения тестов """
    state = UnitCmd.FREE
    
    def __init__(self, addr: int):
        """Инициализирует эмулятор узла

        Параметры:
            addr: Адрес узла
        """
        self.addr = addr

    async def execute(self, cmd: bytes, future: Future) -> NoReturn:
        """Принять команду на обработку и вернуть ответ

        Параметры:
            cmd: байт-строка команда
            future: футура, в которую отправляется ответ
        """
        cmd = DispCmd.from_bytes(cmd)
        if cmd.addr != self.addr:
            return
        ans = await self.handle(cmd)
        future.set_result(ans.to_bytes())

    async def handle(self, cmd: DispCmd) -> DispCmd:
        """Обработать входящую команду

        Параметры:
            cmd: принятая команда

        Возврат: ответ узла
        """
        if cmd.cmd == UnitCmd.STATUS:
            ans = DispCmd(0, self.state)
        else:
            ans = DispCmd(0, UnitCmd.ACCEPTED)
            if cmd.cmd == UnitCmd.STOP:
                self.state = UnitCmd.FREE
            elif cmd.cmd == UnitCmd.ERROR_RESOLVED:
                if self.state == UnitCmd.WORK_ERROR:
                    self.state = UnitCmd.FREE
            elif cmd.cmd == UnitCmd.SETUP:
                self.setup = cmd.args
            elif cmd.cmd == UnitCmd.SETUP_ARGS:
                ans.args = self.setup
            else:
                ans.cmd = UnitCmd.CMD_N_FOUND
        return ans
