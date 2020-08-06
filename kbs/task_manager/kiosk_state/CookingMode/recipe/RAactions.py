import asyncio
import time

from .mixins import ToolsMixin, ConfigMixin

from kbs.ra_api.RA import RA
from kbs.ra_api.RA import RAError


class BaseRA(ToolsMixin):
    """ Это класс дописать """

    @staticmethod
    async def get_current_position():
        """Этот метод возвращает место, куда едет RA"""

        return await RA.get_current_position()

    @staticmethod
    async def get_movement_duration(place_from, place_to, time_limit=None):
        """ Метод получает варианты длительности передвижения, выбирает тот, который
        удовлетворяет условиям
        :param place_from: str
        :param place_to: str
        :param time_limit: datetime.time
        :return: int
        :raise RAError

        """
        possible_duration = await RA.get_position_move_time(place_from, place_to)
        if possible_duration and time_limit:
            time_gap = time_limit - time.time()
            time_options = list(filter(lambda t: t <= time_gap, possible_duration))
            print(f"Возможные варианты доезда при активном лимите {possible_duration}, "
                  f"выбрано {max(time_options) if time_options else min(possible_duration)}")
            print()
            return max(time_options) if time_options else min(possible_duration)
        elif possible_duration:
            print(f"Возможные варианты доезда{possible_duration}, выбрано {min(possible_duration)}")
            print()
            return min(possible_duration)
        if not possible_duration:
            raise RAError

    @staticmethod
    async def get_atomic_chain_duration(atomic_info):
        """ Этот метод получает длительность группы атомарных действий в сек
        :param atomic_info:
        :return:

        Где используем этот метод????? Удалить?
        """
        duration = await RA.get_atomic_action_time(**atomic_info)

        if not duration:
            raise RAError
        return duration

    @classmethod
    async def atomic_chain_execute(cls, atomic_params_dict, *args):
        """Этот метод выполняет группу атомарных действий
        :param atomic_params_dict: dict с параметрами (name, place)

        """
        duration = await cls.get_atomic_chain_duration(atomic_params_dict)
        try:
            await RA.start_atomic_action(**atomic_params_dict)
            print(f"PBM {time.time()} - Успешно выполнили атомарное действие", atomic_params_dict["name"])
        except RAError:
            print("Ошибка атомарного действия")


class BaseActionsRA(BaseRA, ConfigMixin):

    async def move_to_object(self, move_params, equipment):
        """Эта функция описывает движение до определенного места.

        ПЕРЕПИСАТЬ документацию

        :param: tuple (place: uuid, limit: bool)
        limit - это флаг для выбора времени на перемещения.
        ra_api одно и тоже движение может выполнить за разное время: мин возможное и "с танцами"
        сам временной лимит, то есть время, в которое нужно приехать
        в конечную точку содержится в self.time_limit

        Если лимит True, то движение туда запускается по мин времени, а обратно
        в зависимости от оставшегося времени. Если есть свободное, "танцуем с продуктом"

        """

        place_to, limit = move_params
        current_location = await self.get_current_position()

        is_limit_active = True if limit and equipment.cut_station.be_free_at else False
        time_limit = equipment.cut_station.be_free_at if is_limit_active else None

        print(f"PBM {time.time()} - Начинаем чейн движения из {current_location} в {place_to}")
        print(f"Лимит движения активирован {is_limit_active}, освободится в {time_limit}")
        # получаем все возможные временные варианты доезда до
        try:
            duration = await self.get_movement_duration(current_location,
                                                        place_to,
                                                        time_limit)
            await RA.position_move(place_to, duration)
            dance_time = await self.is_need_to_dance(limit, equipment.cut_station.be_free_at)
            if dance_time:
                print(f"PBM {time.time()} начинаем танцевать дополнительно {dance_time}")
                await RA.dance_for_time(dance_time)
        except RAError:
            print("Не найден маршрут. Что делать???")

    async def bring_half_staff(self, cell_location_tuple, equipment, *args):
        """ Этот метод запускет доставку компонента из холодильника
        в станцию нарезки

        :param cell_location_tuple: ('d4', (3, 4))
        :param equipment:
        :param args:
        :return:
        """
        print(f"PBM {time.time()} - Начинаем везти продукт")

        # параметры запуска
        cell_location, half_staff_position = cell_location_tuple
        atomic_params = {"name": "get_product",
                         "place": "fridge",
                         "obj": "onion",
                         "cell": cell_location,
                         "position": half_staff_position,
                         }

        move_params_to_fridge = (cell_location, None)
        move_params_to_cut = (self.SLICING, True)

        what_to_do = (
            (self.move_to_object, move_params_to_fridge),
            (self.atomic_chain_execute, atomic_params),
            (self.move_to_object, move_params_to_cut),
        )

        await self.chain_execute(what_to_do, equipment)
        print(f"PBM {time.time()} - Привезли ингредиент начинки в нарезку")

    async def change_gripper(self, required_gripper,  equipment):
        """метод, запускающий смену захвата при необходимости """

        current_gripper = await RA.get_current_gripper()
        is_needed_to_change_gripper = await self.is_need_to_change_gripper(current_gripper, required_gripper)

        print(f"PBM {time.time()} - Нужно ли менять захват", is_needed_to_change_gripper)
        print()

        if is_needed_to_change_gripper:
            print(f"PBM {time.time()} Начинаем менять захват с {current_gripper} на {required_gripper}")
            await self.move_to_object((self.CAPTURE_STATION, None), equipment)
            while current_gripper != required_gripper:
                # эмуляция работы)
                if current_gripper is not None:
                    await self.atomic_chain_execute({"place": "gripper_unit", "name": "set_gripper"})
                    await self.atomic_chain_execute({"place": "gripper_unit", "name": "get_gripper"})
                    # Потом удалить, эмуляция работы
                    current_gripper = required_gripper
                else:
                    await self.atomic_chain_execute({"place": "gripper_unit", "name": "get_gripper"})
                    # Потом удалить, эмуляция работы
                    current_gripper = required_gripper

    async def get_vane_from_oven(self, oven_unit, *args):
        """Этот метод запускает группу атомарных действий ra_api по захвату лопатки из печи"""

        atomic_params = {"name": "get_vane_from_oven",
                         "place": oven_unit}
        await self.atomic_chain_execute(atomic_params)

    async def set_vane_in_oven(self, *args):
        """Этот метод запускает группу атомарных действий ra_api по размещению лопатки в печи"""
        oven_id = self.oven_unit
        atomic_params = {"name": "set_shovel",
                         "place": oven_id}

        await self.atomic_chain_execute(atomic_params)

    async def leave_vane_in_cut_station(self, *args):
        """отдаем команду оставить лопатку в станции нарезки"""
        atomic_params = {"name": "set_shovel",
                         "place": self.SLICING}
        await self.atomic_chain_execute(atomic_params)

    # не объединено с выше в 1, так как обработка ошибок может быть разная
    async def take_vane_from_cut_station(self, *args):
        """отдаем команду взять лопатку в станции нарезки"""
        atomic_params = {"name": "get_shovel",
                         "place": self.SLICING}
        await self.atomic_chain_execute(atomic_params)

    async def control_dough_position(self, *args):
        """отдаем команду на поправление теста"""
        atomic_params = {"name": "get_dough",
                         "place": self.dough.halfstuff_cell}
        await self.atomic_chain_execute(atomic_params)

    async def put_half_staff_in_cut_station(self, *args):
        """Этот метод опускает п-ф в станцию нарезки"""
        print(f"PBM {time.time()} - Начинаем размещать продукт в станции нарезки")

        _, equipment = args

        print("Станция нарезки свободна", equipment.cut_station.is_free.is_set())

        atomic_params = {
            "name": "set_product",
            "place": self.SLICING
        }

        while not equipment.cut_station.is_free.is_set() and not self.is_dish_failed:
            print(f"PBM {time.time()} Станция нарезки занята, танцуем с продуктом")
            print()
            await asyncio.sleep(1)
            # добавить вызов ra_api танец с продуктом

        await self.atomic_chain_execute(atomic_params)

        equipment.cut_station.is_free.clear()

    async def dish_packaging(self):
        """Этот метод запускает группу атомарных действий по упаковке пиццы"""
        print("Начинаем упаковывать блюдо ra_api", time.time())
        atomic_params = {
            "name": "pack_pizza",
            "place": self.PACKING
        }
        await self.atomic_chain_execute(atomic_params)

    async def dish_extradition(self):
        """Этот метод запускает группу атомарных действий по выдаче пиццы"""
        print("Выдаем пиццу в узел выдачи", time.time())
        atomic_params = {
            "name": "set_pizza",
            "place": self.GIVE_OUT
        }
        await self.atomic_chain_execute(atomic_params)

    async def switch_vane(self):
        """Этот метод запускает группу атомарных действий по смене лопакок при выдаче"""
        print("Запускаем смену лопаток с выдачи на для пиццы")
        atomic_params = {
            "name": "get_shovel",
            "place": self.PACKING
        }
        await self.atomic_chain_execute(atomic_params)
