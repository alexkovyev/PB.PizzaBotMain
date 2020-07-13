from apscheduler.schedulers.asyncio import AsyncIOScheduler


def create_scheduler(self):
    """Этот метод создает планировщик для запуска команд по расписанию,
    например, включение рабочего режима каждый день в заданное время
    :return экземпляр класса AsyncIOScheduler
    """

    scheduler = AsyncIOScheduler()
    scheduler.add_job(self.turn_on_cooking_mode, 'cron', day_of_week='*', hour='10', minute=0, second=0)
    scheduler.add_job(self.turn_off_cooking_mode, 'cron', day_of_week='*', hour='21', minute=0, second=0)
    return scheduler