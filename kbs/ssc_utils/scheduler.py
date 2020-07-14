from apscheduler.schedulers.asyncio import AsyncIOScheduler

from kbs.data.kiosk_modes.kiosk_modes import KioskModeNames


class PbmScheduler(object):

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def jobs_planned(self):
        """Этот метод создает планировщик для запуска команд по расписанию,
        например, включение рабочего режима каждый день в заданное время
        :return экземпляр класса AsyncIOScheduler
        """

        self.scheduler.add_job(self.turn_on_cooking_mode, 'cron', day_of_week='*', hour='10', minute=0, second=0)
        self.scheduler.add_job(self.turn_off_cooking_mode, 'cron', day_of_week='*', hour='21', minute=0, second=0)

    async def turn_on_cooking_mode_scheduler(self):
        IMPOSSIBLE_TO_TURN_ON_STATES = [KioskModeNames.TESTINGMODE,
                                        KioskModeNames.COOKINGMODE,
                                        KioskModeNames.BEFORECOOKING]

    async def turn_on_cooking_mode(self):
        """Этот метод обрабатывает запуск режима готовки по расписанию"""
        IMPOSSIBLE_TO_TURN_ON_STATES = [KioskModeNames.TESTINGMODE,
                                        KioskModeNames.COOKINGMODE,
                                        KioskModeNames.BEFORECOOKING]
        if self.current_state == KioskModeNames.STANDBYMODE:
            await self.cooking_mode_start()
        elif self.current_state in IMPOSSIBLE_TO_TURN_ON_STATES:
            print("киоск занят, не могу включить")
        print("Режим готовки активирован", self.current_state)


# def create_scheduler(self):
#     """Этот метод создает планировщик для запуска команд по расписанию,
#     например, включение рабочего режима каждый день в заданное время
#     :return экземпляр класса AsyncIOScheduler
#     """
#
#     scheduler = AsyncIOScheduler()
#     scheduler.add_job(self.turn_on_cooking_mode, 'cron', day_of_week='*', hour='10', minute=0, second=0)
#     scheduler.add_job(self.turn_off_cooking_mode, 'cron', day_of_week='*', hour='21', minute=0, second=0)
#     return scheduler
