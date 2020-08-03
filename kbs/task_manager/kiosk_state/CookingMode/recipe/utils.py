import time

from kbs.ra_api.RA import RA


class DurationEvaluation(RA):

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
        time_to_get = await RA.get_atomic_action_time(**atomic_params)
        print("Это время атомарного действия", time_to_get)
        time_to_move_back_options = await RA.get_position_move_time(cell_location, self.SLICING)

        time_limit = equipment.cut_station.be_free_at
        time_gap = time_left + min(time_to_move_back_options) + time_to_move_to + time_to_get

        print("Время на смену захвата", time_left)
        print("Время доезда до холодильника", time_to_move_to)
        print("Это время атомарного действия", time_to_get)
        print("Это лимит времени по станции нарезки", time_limit)
        print("Это time gap на весь чейн", time_gap)
        print(time.time())
        print("Чейн закончится в ", (time.time() + time_gap))

        if time_limit is not None:
            if (time.time() + time_gap) > time_limit:
                time_to_move_back = min(time_to_move_back_options)
                print("Время обратно если с лимитом и минимальным значением", time_to_move_back)
            else:
                time_to_move_back = equipment.cut_station.be_free_at - time.time()
                print("Время без лимита как разница", time_to_move_back)
        else:
            time_to_move_back = min(time_to_move_back_options)

        atomic_params = {
            "name": "set_product",
            "place": self.SLICING
        }

        time_to_put_item = await RA.get_atomic_action_time(**atomic_params)

        total_time = time_to_move_to + time_to_get + time_to_move_back + time_to_put_item

        print("Это возвращает функция пф", total_time)

        return total_time


    async def time_to_bring_vane(self):

        atomic_params = {"name": "get_shovel",
                         "place": self.SLICING}

        oven = self.oven_unit.oven_id

        atomic_params_2 = {"name": "set_shovel",
                         "place": oven}

        time_total = min(await RA.get_position_move_time(oven, self.SLICING))

        time_total += await RA.get_atomic_action_time(**atomic_params)
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
        is_need_change_gripper = await self.is_need_to_change_gripper(current_gripper, "product")

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

