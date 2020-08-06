import asyncio
import time

from kbs.cntrls_api.ControllerBus import Controllers
from kbs.exceptions import ControllersFailedError


class BaseActionsControllers():

    @staticmethod
    async def get_dough(dough_point, *args):
        """отдает команду контролеру получить тесто"""
        print(f"PBM {time.time()} Получаем тесто у контроллеров")
        print()

        operation_result = await Controllers.give_dough(dough_point)

        if operation_result:
            print(f"PBM {time.time()} успешно получили тесто у контроллеров")
        else:
            print(f"PBM {time.time()}Ошибка получения теста у контроллеров")
            raise ControllersFailedError
        # запускает метод списать п\ф через Mixin

    @staticmethod
    async def give_sauce(equipment, sauce_recipe):
        """Вызов метода контроллеров для поливания соусом
        или добавкой """
        print(f"PBM {time.time()} Начинаем поливать соусом")
        print()

        await equipment.cut_station.set_occupied()
        operation_result = await Controllers.give_sauce(sauce_recipe)

        if operation_result:
            print(f"PBM {time.time()} успешно полили соусом")
            await equipment.cut_station.set_free()
        else:
            print(f"PBM {time.time()}Ошибка контроллеров при поливании соусом")
            raise ControllersFailedError
        # запускает метод списать п\ф через Mixin

    async def cut_half_staff(self, cutting_program, equipment, is_last_item=False):
        print("Начинаем этап ПОРЕЖЬ продукт", time.time())
        duration = cutting_program["duration"]
        program_id = cutting_program["program_id"]
        print("Время начала нарезки п\ф", time.time())
        equipment.cut_station.be_free_at = time.time() + cutting_program["duration"]
        print("Это время в оборудовании из контроллеров", equipment.cut_station.be_free_at)
        result = await Controllers.cut_the_product(program_id)
        if result:
            print("успешно нарезали п\ф", time.time())
            equipment.cut_station.is_free.set()
            equipment.cut_station.be_free_at = None
            print("СНЯТ временой ЛИМИТ в", time.time())
            if is_last_item:
                await Controllers.give_sauce()
        else:
            print("---!!! Не успешно нарезали п\ф")
            await self.mark_dish_as_failed()
        print("СТАТУС блюда в нарезке", self.status)

    async def give_paper(self):
        print("Контроллеры начинают выдавать бумагу", time.time())
        result = await Controllers.give_paper()
        if result:
            pass
        else:
            print("Неудача с бумагой")
            await self.mark_dish_as_failed()

            # расписать какая ошибка: - замятие бумаги или полная поломка
            # если замятие, добавить вызов ra_api на уборку бумаги

    async def controllers_turn_heating_on(self, time_gap, is_ready_for_baking):
        """Метод запускает прогрев печи"""
        print("Начинаем ждать запуск прогрева печи", time.time())

        oven_mode = "pre_heating"
        recipe = self.pre_heating_program

        await asyncio.sleep(time_gap)
        operation_result = await Controllers.start_baking(self.oven_unit.oven_id, oven_mode,
                                                          recipe)
        print("Закончили прогрев печи", time.time())

        if operation_result:
            await is_ready_for_baking.wait()
            await self.controllers_bake()

    async def controllers_bake(self, *args):
        """Метод запускает выпечку"""
        print("Начинаем выпечку", time.time())
        oven_mode = "baking"
        recipe = self.baking_program
        self.status = "baking"
        time_changes = asyncio.get_running_loop().create_future()
        baking_task = asyncio.create_task(Controllers.start_baking(self.oven_unit.oven_id, oven_mode, recipe,
                                                     time_changes))
        while not time_changes.done():
            await asyncio.sleep(0.0001)
        print("Футура доделала", time.time())
        await self.time_changes_handler(time_changes)

        await baking_task
        if baking_task.done():
            self.is_dish_ready.set()
            print("БЛЮДО ГОТОВО", time.time())
            self.status = "ready"
            self.oven_unit.status = "waiting_15"
            print("Это результат установки", self.is_dish_ready.is_set())