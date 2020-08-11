import asyncio
import time

from kbs.cntrls_api.ControllerBus import Controllers
from kbs.exceptions import ControllersFailedError


class BaseActionsControllers():

    @staticmethod
    async def get_dough(*args):
        """отдает команду контролеру получить тесто"""
        print(f"PBM {time.time()} Получаем тесто у контроллеров")
        print()

        print(args)

        *_, dish = args

        dough_point = dish.dough.halfstuff_cell

        operation_result = await Controllers.give_dough(dough_point)

        if operation_result:
            print(f"PBM {time.time()} успешно получили тесто у контроллеров")
        else:
            print(f"PBM {time.time()}Ошибка получения теста у контроллеров")
            raise ControllersFailedError
        # запускает метод списать п\ф через Mixin

    @staticmethod
    async def give_sauce(sauce_recipe, duration, equipment):
        """Вызов метода контроллеров для поливания соусом
        или добавкой """
        print(f"PBM {time.time()} Начинаем поливать соусом или добавкой")
        print()

        await equipment.cut_station.set_occupied(duration)
        operation_result = await Controllers.give_sauce(sauce_recipe)

        if operation_result:
            print(f"PBM {time.time()} успешно полили соусом")
            await equipment.cut_station.set_free()
        else:
            print(f"PBM {time.time()}Ошибка контроллеров при поливании соусом")
            raise ControllersFailedError
        # запускает метод списать п\ф через Mixin

    async def cut_half_staff(self, cutting_program, equipment, dish, is_last_item=False):
        """Этот метод нарезает п-ф
         :param cutting_program
         :param equipment
         :param dish
         :param is_last_item
         """

        print("Начинаем этап ПОРЕЖЬ продукт", time.time())

        duration = cutting_program["duration"]
        program_id = cutting_program["program_id"]

        await equipment.cut_station.set_occupied(duration)

        result = await Controllers.cut_the_product(program_id)

        if result:
            print("успешно нарезали п\ф", time.time())
            await equipment.cut_station.set_free()

            if is_last_item:
                additive_recipe = dish.additive.halfstuff_cell
                duration = dish.additive.duration
                await asyncio.create_task(self.give_sauce(additive_recipe,
                                                          duration,
                                                          equipment))

        else:
            print("---!!! Не успешно нарезали п\ф")
            await dish.mark_dish_as_failed()
        print("СТАТУС блюда в нарезке", dish.status)

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

    async def controllers_oven(self, recipe, dish):
        """Это основной метод взаимодействия с печью """

        oven_id = dish.oven_unit.oven_id
        time_changes = asyncio.get_running_loop().create_future()
        oven_task = asyncio.create_task(Controllers.start_baking(oven_id, recipe,
                                                     time_changes))

        while not time_changes.done():
            await asyncio.sleep(0.0001)

        await dish.time_changes_handler(time_changes)
        await oven_task
        print("Это результат таска c печью", oven_task.result())

        return oven_task.result()

    async def controllers_turn_heating_on(self, dish, time_gap, is_ready_for_baking):
        """Метод запускает прогрев печи"""

        print("Начинаем ждать запуск прогрева печи", time.time())

        recipe = dish.oven_recipes["pre_heating_program"]
        await asyncio.sleep(time_gap)
        operation_result = await self.controllers_oven(recipe, dish)

        print("Закончили прогрев печи", time.time())

        if operation_result:
            await is_ready_for_baking.wait()
            await self.controllers_bake(dish)

    async def controllers_bake(self, dish, *args):
        """Метод запускает выпечку"""
        print("Начинаем выпечку", time.time())

        recipe = dish.oven_recipes["cooking_program"]
        dish.status = "baking"

        print("Это номер рецепта",recipe)

        operation_result = await self.controllers_oven(recipe, dish)

        print("Закончили выпечку")

        print("Вот результат", operation_result)

        if operation_result:
            dish.is_dish_ready.set()
            print("БЛЮДО ГОТОВО", time.time())
            dish.status = "ready"
            dish.oven_unit.status = "waiting_15"
            print("Это результат установки", dish.is_dish_ready.is_set())
