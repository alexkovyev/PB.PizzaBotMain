from .BaseMode import BaseMode


class TestingMode(object):
    def __init__(self):
        super.__init__()
        self.status = "Тестируем"

    async def hello_from(self):
        print("Привет из теста", asyncio.sleep(10))
