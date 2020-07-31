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

    async def prepare_dough_and_sauce(self, *args):
        """Метод рецепта, описываюший этап возьи тесто и полей соусом
        Это bound-method к блюду, поэтому доступны все атрибуты
        экземпляра класса Dish
        """
        print(f"PBM {time.time()} - Начинается chain Возьми ТЕСТО")
        print()

        _, equipment = args

        to_do = ((self.change_gripper, "None"),
                 (self.move_to_object, (self.oven_unit, None)),
                 (self.get_vane_from_oven, None),
                 (self.move_to_object, (self.SLICING, None)),
                 (self.get_dough, None),
                 (self.control_dough_position, None),
                 (self.move_to_object, (self.SLICING, None)),
                 (self.leave_vane_in_cut_station, None),
        )

        await self.prepare_cooking()
        await self.chain_execute(to_do, equipment)

        print(f"PBM {time.time()} - Закончили с ТЕСТОМ, статус блюда {self.status}")
        print()

        if not self.is_dish_failed:
            asyncio.create_task(self.give_sauce(equipment))

    async def prepare_filling_item(self, *args):
        """Чейн по доставке и нарезки 1 п\ф
        args: (params, equipment)

        """
        # print("Это аргс из начинки", args)
        filling_data, equipment = args
        filling_item = filling_data["id"]
        cutting_program = filling_data["cut_program"]
        storage_adress = filling_data["location"]
        is_last_item = filling_data["is_last"]

        to_do = (
            (self.change_gripper, "product"),
            (self.bring_half_staff, storage_adress),
            (self.put_half_staff_in_cut_station, None),
                 )

        await asyncio.sleep(0.2)
        print(f"PBM - {time.time()} Начинаем готовить {filling_item.upper()}")

        if is_last_item:
            await asyncio.sleep(0.1)
            time_to_do = await self.time_calculation(storage_adress, equipment, cutting_program)

            time_gap_to_heating = time_to_do - 15

            print(f"PBM {time.time()} - Запустили прогрев")
            heating_task = asyncio.create_task(self.controllers_turn_heating_on(time_gap_to_heating))

        await self.chain_execute(to_do, equipment)

        if not self.is_dish_failed:
            asyncio.create_task(self.cut_half_staff(cutting_program, equipment))
            print(f"PBM {time.time()} - Запустили нарезку п-ф в очередь")
            print()

            if is_last_item:
                await self.change_gripper("None", equipment)

                while heating_task.done():
                    await asyncio.sleep(0.1)
                await self.start_baking(None, equipment)

    async def time_for_change_gripper(self, current_location, current_gripper):

        time_to_move = min(await RA.get_position_move_time(current_location,
                                                    self.CAPTURE_STATION))
        time_to_change = 0
        if current_gripper is not None:
            time_to_change = await self.get_atomic_chain_duration(
                {"place": "gripper_unit", "name": "set_gripper"})
            time_to_change += await self.get_atomic_chain_duration(
                {"place": "gripper_unit", "name": "get_gripper"})
        else:
            time_to_change = await self.get_atomic_chain_duration(
                {"place": "gripper_unit", "name": "get_gripper"})

        total_time = time_to_move + time_to_change

        return total_time

    async def time_to_bring_half_staff(self, cell_location_tuple, current_location,
                                       equipment, time_left):
        cell_location, half_staff_position = cell_location_tuple
        atomic_params = {"name": "get_product",
                         "place": "fridge",
                         "obj": "onion",
                         "cell": cell_location,
                         "position": half_staff_position,
                         }

        print("Считаем время привоза п-ф")
        time_to_move_to = min(await RA.get_position_move_time(current_location, cell_location))
        print("Это время поездки до холодилника", time_to_move_to)
        time_to_get = await RA.get_atomic_action_time(**atomic_params)
        print("Это время атомарного действия", time_to_get)
        time_to_move_back_options = await RA.get_position_move_time(cell_location, self.SLICING)

        time_limit = equipment.cut_station.be_free_at
        time_gap = time_left + min(time_to_move_back_options) + time_to_move_to + time_to_get

        print("Это лимит времени по станции нарезки", time_limit)
        print("Это время до плюс минимальное обратно", time_gap)

        if time_limit is not None:
            if (time.time() + time_gap) > time_limit:
                time_to_move_back = min(time_to_move_back_options)
                print("Время если с лимитом и минимальным значением", time_to_move_back)
            else:
                time_to_move_back = equipment.cut_station.be_free_at - time.time()
                print("Время без лимита как разница", time_to_move_back)
        else:
            time_to_move_back = min(time_to_move_back_options)

        total_time = time_to_move_to + time_to_get + time_to_move_back

        return total_time


    async def time_to_bring_vane(self):

        atomic_params = {"name": "get_shovel",
                         "place": self.SLICING}

        oven = self.oven_unit.oven_id

        atomic_params_2 = {"name": "set_shovel",
                         "place": oven}

        time_total = await RA.get_atomic_action_time(**atomic_params)
        print(time_total)

        time_total += min(await RA.get_position_move_time(self.SLICING, oven))

        print(time_total)

        time_total += await RA.get_atomic_action_time(**atomic_params_2)

        print(time_total)

        return time_total


    async def time_calculation(self, storage_adress, equipment, cutting_program):
        time_left = 0
        current_gripper = await RA.get_current_gripper()
        current_location = await RA.get_current_position()
        is_need_change_gripper = await self.is_need_to_change_gripper(current_gripper, "None")

        if is_need_change_gripper:
            print("ОЦЕНКА нужно менять захват")
            time_left += await self.time_for_change_gripper(current_location,current_gripper)
            print("Время со сменой", time_left)
            current_location = self.CAPTURE_STATION

        print("Это время освобождения станции нарезки", equipment.cut_station.be_free_at)

        time_left += await self.time_to_bring_half_staff(storage_adress,
                                                      current_location,
                                                      equipment,
                                                      time_left)

        print("Время со смено 2", time_left)

        time_left += cutting_program["duration"]

        print("Время со сменой 3", time_left)

        time_left += await self.time_to_bring_vane()

        print("ИТОГОвое время", time_left)

        return time_left


    async def start_baking(self, *args):
        """Этот метод транспортрует лопатку в печь и запускает выпечку"""
        print("Начинаем чейн Вези лопатку в печь")
        # print("Это аргс из начинки", args)
        _, equipment = args

        chain_list = [(self.move_to_object, (self.SLICING, None)),
                      (self.take_vane_from_cut_station, None),
                      (self.move_to_object, (self.oven_unit, None)),
                      (self.set_vane_in_oven, "heating"),
                      ]

        print("СТАНЦИЯ НАРЕЗКИ СВОБОДНА", equipment.cut_station.is_free.is_set())
        while not equipment.cut_station.is_free.is_set():
            print("Танцеуем")
            await RA.dance()

        await self.chain_execute(chain_list, equipment)
        print("Оставили лопатку в печи", time.time())
        self.status = "baking"
        # if self.status != "failed_to_be_cooked":
        #     asyncio.create_task(self.controllers_bake())
        # print("ЗАКОНЧИЛИ С БЛЮДОМ", time.time())
        # print("СТАТУС блюда после доставки лопатки в печь", self.status)

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