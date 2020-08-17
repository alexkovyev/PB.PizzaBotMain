"""
Это описание что тут воообще будет"""

import time

from .RAactions import BaseRA
from kbs.ra_api.RA import RA
from .mixins import ConfigMixin


class DurationEvaluation(RA, ConfigMixin):
    """Это классный класс, который собирает методы расчета времени"""

    async def time_for_change_gripper(self, current_location, current_gripper):
        """Этот метод считает время на смену захвата"""

        time_to_move = min(await RA.get_position_move_time(current_location,
                                                           self.CAPTURE_STATION))
        time_to_change = 0

        if current_gripper is not None:
            time_to_change = await BaseRA.get_atomic_chain_duration(
                {"place": "gripper_unit", "name": "set_gripper"})
            time_to_change += await BaseRA.get_atomic_chain_duration(
                {"place": "gripper_unit", "name": "get_gripper"})
        else:
            time_to_change = await BaseRA.get_atomic_chain_duration(
                {"place": "gripper_unit", "name": "get_gripper"})

        total_time = time_to_move + time_to_change

        return total_time

    async def time_to_move_to_cut(self, equipment, cell_location, time_gap):

        time_limit = equipment.cut_station.be_free_at

        time_to_move_back_options = await RA.get_position_move_time(cell_location, self.SLICING)

        time_to_move_back = min(time_to_move_back_options)

        time_gap += time_to_move_back

        print("Это лимит времени по станции нарезки", time_limit)

        print("Это мин время на весь чейн", time_gap)
        print(time.time())
        print("Чейн закончится в ", (time.time() + time_gap))

        if time_limit is not None:
            if (time.time() + time_gap) > time_limit:
                # time_to_move_back = min(time_to_move_back_options)
                print("Время обратно если с лимитом и минимальным значением", time_to_move_back)
            else:
                time_to_move_back = equipment.cut_station.be_free_at - time.time()
                print("Нарезка занята, поэтому время вот такое", time_to_move_back)

        return time_to_move_back


    async def time_to_bring_half_staff(self, cell_location_tuple, current_location,
                                       equipment, time_to_change_gripper):
        """

        :param cell_location_tuple:
        :param current_location:
        :param equipment:
        :param time_to_change_gripper:
        :return:
        """
        cell_location, half_staff_position = cell_location_tuple
        atomic_params = {"name": "get_product",
                         "place": "fridge",
                         "obj": "onion",
                         "cell": cell_location,
                         "position": half_staff_position,
                         }

        time_to_move_to = min(await RA.get_position_move_time(current_location, cell_location))
        time_to_get = await RA.get_atomic_action_time(**atomic_params)

        time_gap = time_to_change_gripper + time_to_move_to + time_to_get

        print("Время на смену захвата", time_to_change_gripper)
        print("Время доезда до холодильника", time_to_move_to)
        print("Это время атомарного действия", time_to_get)

        time_to_move_back = await self.time_to_move_to_cut(equipment, cell_location, time_gap)

        atomic_params = {
            "name": "set_product",
            "place": self.SLICING
        }

        time_to_put_item = await RA.get_atomic_action_time(**atomic_params)

        total_time = time_to_move_to + time_to_get + time_to_move_back + time_to_put_item

        print("Это возвращает функция пф", total_time)

        return total_time

    async def time_to_bring_vane(self, oven_id):
        """

        :return:
        """
        atomic_params = {"name": "get_shovel",
                         "place": self.SLICING}

        atomic_params_2 = {"name": "set_shovel",
                           "place": oven_id}

        time_total = min(await RA.get_position_move_time(oven_id, self.SLICING))

        time_total += await RA.get_atomic_action_time(**atomic_params)

        time_total += min(await RA.get_position_move_time(self.SLICING, oven_id))

        time_total += await RA.get_atomic_action_time(**atomic_params_2)

        return time_total

    async def time_calculation(self, storage_address, equipment,
                               cutting_program, additive_time,
                               oven_id):
        """Этот метод считает время, необходимое для завершения готовки текущего блюда """

        time_left = 0

        current_gripper = await RA.get_current_gripper()
        current_location = await RA.get_current_position()
        is_need_change_gripper = await BaseRA.is_need_to_change_gripper(current_gripper, "product")

        if is_need_change_gripper:
            time_left += await self.time_for_change_gripper(current_location, current_gripper)
            current_location = self.CAPTURE_STATION

        time_left += await self.time_to_bring_half_staff(storage_address,
                                                         current_location,
                                                         equipment,
                                                         time_left)

        print("Время gripper и привези", time_left)

        time_left += cutting_program["duration"]

        print("Время gripper, привези и нарежь ", time_left)

        # время на добавку

        time_left += additive_time

        print("Время с поливкой добавкой", time_left)

        time_left += await self.time_to_bring_vane(oven_id)

        print("ИТОГОвое время", time_left)

        return time_left

    async def delivery_time_calculation(self, dish, current_location, current_gripper):
        if current_gripper != None:
            total_time = await self.time_for_change_gripper(current_location, current_gripper)
        else:
            total_time = 0

