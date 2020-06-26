import asyncio

from .BaseMode import BaseMode


class TestingMode(BaseMode):
    def __init__(self):
        super().__init__()
        self.status = "Тестируем"
