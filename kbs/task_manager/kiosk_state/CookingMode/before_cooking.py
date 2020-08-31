import asyncio
import concurrent.futures
import multiprocessing
import time

from functools import partial

from kbs.redis.recipe_data import recipe_data
from kbs.task_manager.kiosk_state.BaseMode import BaseMode
from kbs.cntrls_api.ControllerBus import Controllers
from kbs.data.kiosk_modes.kiosk_modes import KioskModeNames


class BeforeCooking(BaseMode):

    def __init__(self):
        super().__init__()

    @classmethod
    def start_testing(clx, equipment_data):
        """Тут вызываем методы контролеров по тестированию оборудования"""
        # вызывается какой то супер метод контроллеров на проверку,
        # возвращает status и dict с данными об оборудовании
        # не сделано, заглушка
        is_equipment_ok = True
        print("Начинаем тестировать оборудования", time.time())
        time.sleep(4)
        equipment_data.controllers = Controllers()
        print("Оборудование протестировано, исправно", time.time())
        return is_equipment_ok, equipment_data

    @classmethod
    def parse_recipes(clx):
        """Парсит все рецепты в директории и возвращает словарь вида:
        не сделано, заглушка
        """
        print("Начинаем парсить рецепты", time.time())
        time.sleep(4)
        print("Рецепты спарсены", time.time())
        recipes = recipe_data
        return recipes

    @classmethod
    async def start_cooking(clx, equipment_data):
        """Этот метод запускает режим готовки. Так как это блокирующие операции,
        используется run_in_executor"""
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        my_loop = asyncio.get_running_loop()

        async def task_1(equipment_data):
            is_equipment_ok, equipment_data = await my_loop.run_in_executor(pool,
                                                                            partial(clx.start_testing,
                                                                                    equipment_data))
            return is_equipment_ok, equipment_data

        async def task_2():
            recipes = await my_loop.run_in_executor(pool, clx.parse_recipes)
            return recipes

        task_1 = my_loop.create_task(task_1(equipment_data))
        task_2 = my_loop.create_task(task_2())
        my_result = await asyncio.gather(task_1, task_2)
        return my_result

    def __str__(self):
        return KioskModeNames.BEFORECOOKING