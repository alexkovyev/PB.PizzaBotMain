"""Пока тут собрана информация о рецепте.
Доделано по "сути", не сделан рефакторинг и проверка на адекватность
"""
import asyncio
import time

from .ControllersActions import BaseActionsControllers
from .RAactions import BaseActionsRA

from kbs.ra_api.RA import RA
from kbs.cntrls_api.ControllerBus import Controllers


class DishRecipe(BaseActionsRA, BaseActionsControllers):

    # async def prepare_dough_and_sauce(self, *args):
    #     """Метод рецепта, описываюший этап возьи тесто и полей соусом
    #     Это bound-method к блюду, поэтому доступны все атрибуты
    #     экземпляра класса Dish
    #     """
    #     print(f"PBM {time.time()} - Начинается chain Возьми ТЕСТО")
    #     print()
    #
    #     _, equipment = args
    #
    #     to_do = ((self.change_gripper, "None"),
    #              (self.move_to_object, (self.oven_unit, None)),
    #              (self.get_vane_from_oven, None),
    #              (self.move_to_object, (self.SLICING, None)),
    #              (self.get_dough, None),
    #              (self.control_dough_position, None),
    #              (self.move_to_object, (self.SLICING, None)),
    #              (self.leave_vane_in_cut_station, None),
    #              )
    #
    #     await self.prepare_cooking()
    #     await self.chain_execute(to_do, equipment)
    #
    #     print(f"PBM {time.time()} - Закончили с ТЕСТОМ, статус блюда {self.status}")
    #     print()
    #
    #     if not self.is_dish_failed:
    #         asyncio.create_task(self.give_sauce(equipment))
    #
    # async def prepare_filling_item(self, *args):
    #     """Чейн по доставке и нарезки 1 п\ф
    #     args: (params, equipment)
    #
    #     """
    #     # print("Это аргс из начинки", args)
    #     filling_data, equipment = args
    #     filling_item = filling_data["id"]
    #     cutting_program = filling_data["cut_program"]
    #     storage_address = filling_data["location"]
    #     is_last_item = filling_data["is_last"]
    #
    #     to_do = (
    #         (self.change_gripper, "product"),
    #         (self.bring_half_staff, storage_address),
    #         (self.put_half_staff_in_cut_station, None),
    #     )
    #
    #     await asyncio.sleep(0.2)
    #     print(f"PBM - {time.time()} Начинаем готовить {filling_item.upper()}")
    #
    #     if is_last_item:
    #         await asyncio.sleep(0.1)
    #         time_to_do = await self.time_calculation(storage_address, equipment, cutting_program)
    #
    #         print("Это время в time_calculation", time_to_do)
    #
    #         time_gap_to_heating = time_to_do - 15
    #
    #         print("time_gap", time_gap_to_heating)
    #
    #         is_ready_for_baking = asyncio.Event()
    #
    #         print(f"PBM {time.time()} - Запустили прогрев")
    #         heating_task = asyncio.create_task(self.controllers_turn_heating_on(time_gap_to_heating,
    #                                                                             is_ready_for_baking))
    #
    #     await self.chain_execute(to_do, equipment)
    #
    #     if not self.is_dish_failed:
    #         asyncio.create_task(self.cut_half_staff(cutting_program, equipment))
    #         print(f"PBM {time.time()} - Запустили нарезку п-ф в очередь")
    #         print()
    #
    #         if is_last_item:
    #             await self.change_gripper("None", equipment)
    #             await self.start_baking(None, equipment, is_ready_for_baking)
    #
    # async def start_baking(self, *args):
    #     """Этот метод транспортрует лопатку в печь и запускает выпечку"""
    #     print("Начинаем чейн Вези лопатку в печь")
    #     # print("Это аргс из начинки", args)
    #     _, equipment, is_ready_for_baking = args
    #
    #     chain_list = [(self.move_to_object, (self.SLICING, None)),
    #                   (self.take_vane_from_cut_station, None),
    #                   (self.move_to_object, (self.oven_unit, None)),
    #                   (self.set_vane_in_oven, "heating"),
    #                   ]
    #
    #     print("СТАНЦИЯ НАРЕЗКИ СВОБОДНА", equipment.cut_station.is_free.is_set())
    #     while not equipment.cut_station.is_free.is_set():
    #         print("Танцеуем")
    #         await RA.dance()
    #
    #     await self.chain_execute(chain_list, equipment)
    #     print("Оставили лопатку в печи", time.time())
    #     self.status = "baking"
    #     is_ready_for_baking.set()

    async def make_crust(self):
        print("Начинаем разогрев пиццы")
        oven_mode = "make_crust"
        recipe = self.make_crust_program
        time_changes = asyncio.get_running_loop().create_future()
        await self.time_changes_handler(time_changes)
        operation_results = await Controllers.start_baking(self.oven_unit.oven_id, oven_mode, recipe, time_changes)
        return operation_results

    async def dish_packing_and_deliver(self):
        print("Начинаем упаковку пиццы")
        chain_list = [(self.change_gripper, "None"),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.get_vane_from_oven, None),
                      (self.move_to_object, (self.PACKING, None)),
                      (self.dish_packaging, None),
                      (self.move_to_object, (self.pickup_point_unit, None)),
                      (self.dish_extradition, None),
                      (self.move_to_object, (self.PACKING, None)),
                      (self.switch_vane, None),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.set_vane_in_oven, None),
                      ]
        await self.chain_execute(chain_list)
        print("Закончили упаковку и выдачу пиццы")

    async def throwing_dish_away(self):
        print("Запускаем выбрасывание блюда", time.time())
        chain_list = [(self.change_gripper, "None"),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.get_vane_from_oven, None),
                      (self.move_to_object, (self.GARBAGE_STATION, None)),
                      (self.move_to_object, (self.oven_unit, None)),
                      ]
        await self.chain_execute(chain_list)
        self.oven_unit.status = "free"
        self.oven_unit.dish = None
        self.status = self.STOP_STATUS
        print("Закончили выбрасывание блюда")

    async def switch_vanes(self, broken_oven_unit):
        print("Запускаем смену лопаток между печами")
        # не доделано
        chain_list = [(self.move_to_object, (broken_oven_unit, None)),

                      (),
                      ]

    async def switch_vane_cut_oven(self, new_oven_id, old_oven_id, *args):
        print("Меняем лопатку между станцией нарезки и печью")
        chain_list = [(self.move_to_object, (new_oven_id, None)),
                      (self.get_vane_from_oven, new_oven_id),
                      (self.move_to_object, (old_oven_id, None)),
                      (self.set_vane_in_oven, old_oven_id)
                      ]
        await self.chain_execute(chain_list)
        # что будет если неудачно?
