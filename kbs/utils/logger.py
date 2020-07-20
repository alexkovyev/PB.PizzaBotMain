# -*- coding: utf-8 -*-

"""
Created on 21.05.2020
:author: goodmice
Constains customized logger class for the project
"""

import os
import logging
import datetime
from typing import NoReturn
from .colors import TerminalColors

try:
    __KBS_DEFAULT_LOG_DIR__
except NameError:
    __KBS_DEFAULT_LOG_DIR__ = r'./logs/'


class CustomFormatter(logging.Formatter):
    """ Formatting to configure the logger """

    def __init__(self, c: str):
        """
        Constructor class CustomFormatter
        :param str c: Color Output Class Instance
        :return: Color Output Class Instance
        :rtype: CustomFormatter
        """

        self.c = c
        logging.Formatter.__init__(self, self.fmt())

    def format(self, record: logging.LogRecord) -> str:
        """
        Modified function 'format'
        :param logging.LogRecord record: Record for formatting
        :return: Format result
        :rtype: str
        """

        self._style = logging.PercentStyle(self.fmt(record.levelno))
        result = logging.Formatter.format(self, record)
        self._style = logging.PercentStyle(self._fmt)
        return result

    def fmt(self, level: int = logging.DEBUG) -> str:
        """
        Formatting a template for displaying log entries
        :param int level: Logging level
        :return: format string format
        :rtype: str
        """

        out = self.c.h(r"%(levelname)s")
        if level == logging.INFO:
            out = self.c.og(r"INFO ")
        elif level == logging.WARNING or level == logging.WARN:
            out = self.c.w(r"WARN ")
        elif level == logging.ERROR:
            out = self.c.f(r"ERROR")
        return f'[{out}] {self.c.ob(r"%(name)s")}->%(funcName)s: %(message)s'


class CustomLogger(logging.Logger):
    """ Customized logger for the project """

    def __init__(self, name: str, log_dir: str = None,
                 withoutcolors: bool = False):
        """
        Class constructor CustomLogger
        :param str name: Logger Name
        :param bool withoutcolors: Does the color log have
        :return: Installed Logger Instance
        :rtype: CustomLogger
        """

        super().__init__(name)
        self.c = TerminalColors()
        if withoutcolors:
            self.c.disable()
        self.log_dir = log_dir or __KBS_DEFAULT_LOG_DIR__
        self.console_setup()
        self.file_setup()

    def console_setup(self) -> NoReturn:
        """ Setting for console output """

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        hformat = CustomFormatter(self.c)
        handler.setFormatter(hformat)
        self.addHandler(handler)

    def file_setup(self) -> NoReturn:
        """ Setting for output to file """

        now = datetime.datetime.now()
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        handler = logging.FileHandler(now.strftime(
            self.log_dir + r'%Y-%m-%d.log'), encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        hformat = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s->%(funcName)s: %(message)s')
        handler.setFormatter(hformat)
        self.addHandler(handler)

    def close(self) -> NoReturn:
        for h in self.handlers[:]:
            h.close()
            self.removeHandler(h)
