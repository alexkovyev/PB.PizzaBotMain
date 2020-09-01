import asyncio

from kbs.ssc_utils.server import Server
from kbs.task_manager.pbm import KioskState
from kbs.ssc_utils.scheduler import PbmScheduler


def launch_app():
    """Этот метод запускает приложение, в том числе:
    - запускается aiohttp сервер
    - иницируется
    - инициируется расписание запуска
    - запускаются фоновые задачи
    """

    app = Server.create_server()
    state = KioskState()
    app["state"] = state
    scheduler = PbmScheduler(state)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(Server.create_on_start_tasks(app, scheduler))
    loop.run_forever()


if __name__ == "__main__":
    launch_app()
