from apscheduler.schedulers.asyncio import AsyncIOScheduler

from kbs.data.kiosk_modes.kiosk_modes import KioskModeNames
from ..task_manager.pbm import pizza_bot_main


class PbmScheduler(object):
    """ Этот класс запускает определенные действия по расписанию, например, включение режима готовки
    каждый день по расписанию
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.add_planned_jobs()

    def add_planned_jobs(self):
        """Этот метод добавляет расписание запуска методов
        """

        self.scheduler.add_job(self.turn_on_cooking_mode_scheduler,
                               'cron', day_of_week='*', hour='13', minute=27, second=30)
        self.scheduler.add_job(self.turn_off_cooking_mode,
                               'cron', day_of_week='*', hour='21', minute=0, second=0)

    @staticmethod
    async def turn_on_cooking_mode_scheduler():
        """ Этот метод обрабатывает включение режима готовки по расписанию.
        ДОДЕЛАТЬ: придумать обработку невозможности включения режима
        """

        IMPOSSIBLE_TO_TURN_ON_STATES = [KioskModeNames.TESTINGMODE,
                                        KioskModeNames.COOKINGMODE,
                                        KioskModeNames.BEFORECOOKING]

        kiosk_current_state = pizza_bot_main.current_state

        if kiosk_current_state not in IMPOSSIBLE_TO_TURN_ON_STATES:
            print("запускаем включение по планровщику")
            await pizza_bot_main.cooking_mode_start()
        else:
            print("киоск занят, не могу включить")

    async def turn_off_cooking_mode(self):
        """Этот метод обрабатывает выключение режима готовки по расписанию
         НЕ сделано :( """
        pass
