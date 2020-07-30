import asyncio
import time

from kbs.cntrls_api.ControllerBus import Controllers


class BaseActionsControllers():

    async def get_dough(self, *args):
        """отдает команду контролеру получить тесто"""
        print(f"PBM {time.time()} Получаем тесто у контроллеров")
        print()
        dough_point = self.dough.halfstuff_cell
        chain_result = await Controllers.give_dough(dough_point)
        if chain_result:
            print(f"PBM {time.time()} успешно получили тесто у контроллеров")
        else:
            print("Ошибка получения теста у контроллеров")
            await self.mark_dish_as_failed()
        # запускает метод списать п\ф

    async def give_sauce(self, equipment):
        """Вызов метода контроллеров для поливания соусом"""
        print(f"PBM {time.time()} Начинаем поливать соусом")
        print()
        equipment.cut_station.is_free.clear()
        recipe = self.sauce.sauce_cell
        result = await Controllers.give_sauce(recipe)
        if result:
            print("успешно полили соусом")
            equipment.cut_station.is_free.set()
            equipment.cut_station.be_free_at = None
        else:
            await self.mark_dish_as_failed()

    async def cut_half_staff(self, cutting_program, equipment):
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

    async def controllers_turn_heating_on(self, time_gap):
        """Метод запускает прогрев печи"""
        print("Начинаем ждать запуск прогрева печи", time.time())

        oven_mode = "pre_heating"
        recipe = self.pre_heating_program

        await asyncio.sleep(time_gap)
        operation_result = await Controllers.start_baking(self.oven_unit.oven_id, oven_mode,
                                                          recipe)
        print("Закончили прогрев печи", time.time())

        if operation_result:
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