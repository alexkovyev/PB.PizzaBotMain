from apscheduler.schedulers.asyncio import AsyncIOScheduler

def create_scheduler(self):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(self.turn_on_cooking_mode, 'interval', hours=24)
    return scheduler

