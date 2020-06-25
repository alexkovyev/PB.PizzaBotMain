from .BaseMode import BaseMode


class StandBy(BaseMode):
    def __init__(self):
        super().__init__()
        self.status = "В режиме ожидания"

    async def hello_from(self):
        print("Привет из stand by", asyncio.sleep(10))
