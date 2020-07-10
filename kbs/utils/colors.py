# -*- coding: utf-8 -*-

"""
Created on 21.05.2020
:author: goodmice
Contains class for work with console colors
"""

from typing import NoReturn


class TerminalColors:
    """ Contains constants and functions for work with console """

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self) -> NoReturn:
        """ Turns off colors """

        self.HEADER = self.OKBLUE = self.OKGREEN = \
            self.WARNING = self.FAIL = self.ENDC = ''

    def ob(self, text: str) -> str:
        """
        Displays blue text
        :param str text: Input text
        :return: Color text
        :rtype: str
        """

        return self.OKBLUE + text + self.ENDC

    def og(self, text: str) -> str:
        """
        Displays green text
        :param str text: Input text
        :return: Color text
        :rtype: str
        """

        return self.OKGREEN + text + self.ENDC

    def h(self, text: str) -> str:
        """
        Displays the title text
        :param str text: Input text
        :return: Color text
        :rtype: str
        """

        return self.HEADER + text + self.ENDC

    def w(self, text: str) -> str:
        """
        Displays the warning text
        :param str text: Input text
        :return: Color text
        :rtype: str
        """

        return self.WARNING + text + self.ENDC

    def f(self, text: str) -> str:
        """
        Displays the error text
        :param str text: Input text
        :return: Color text
        :rtype: str
        """

        return self.FAIL + text + self.ENDC
