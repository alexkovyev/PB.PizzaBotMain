"""Этот модуль содержит информацию об оборудовании"""
import asyncio
import time

from kbs.exceptions import NoFreeOvenError, OvenReservationError, BrokenOvenHandlerError


class Equipment(object):
    """Этот класс собирает информацию о оборудовании в текущий день
    Так выглядит информация о печах {12: {"oven_id": 12, "status": "free"},
                                    23: {"oven_id": 23, "status": "reserved", "dish": 213},
                                    1: {"oven_id": 1, "status": "occupied", "dish": 323,
                                       "limit": int}}
    oven_id:{}, во вложенном словаре oven_id нужен для функции fetch_free_oven

    статусы печи:
    free - свободная
    reserved - зарезервирована
    occupied - пицца внутри
    waiting_15 - ждем первые 15 минут
    waiting_60 - ждем до 60 минут
    cleaning - чистим
    """
    OVEN_STATUSES = ["broken", "free", "reserved", "occupied", "waiting_15", "waiting_60"]

    def __init__(self, equipment_data):
        self.ovens = Ovens(equipment_data["ovens"])
        self.cut_station = CutStation(equipment_data["cut_station"])
        self.package_station = equipment_data["package_station"]
        self.sauce_dispensers = equipment_data["sauce_dispensers"]
        self.dough_dispensers = equipment_data["dough_dispensers"]
        self.pick_up_points = equipment_data["pick_up_points"]

    async def is_able_to_cook_checker(self):
        """Этот метод проверяет можно ли готовить, то есть работает ли мин необходмое оборудование, те
        - станция нарезки
        - станция упаковки
        - хотя бы 1 из улов выдачи
        """
        # is_cut_station_ok = self.cut_station.values()
        is_cut_station_ok = self.cut_station
        is_package_station_ok = True if any(self.package_station.values()) else False
        return True if (is_cut_station_ok and is_package_station_ok) else False


class Ovens(object):
    def __init__(self, ovens_data):
        self.oven_units = {i: OvenUnit(ovens_data[i]) for i in ovens_data}

    async def get_oven_by_id(self, oven_id):
        try:
            oven_object = self.oven_units[oven_id]
            return oven_object
        except KeyError:
            raise BrokenOvenHandlerError

    # async def get_oven_status(self, oven_id):
    #     try:
    #         oven_object = await self.get_oven_by_id(oven_id)
    #         oven_status = oven_object.status
    #         return oven_status
    #     except (KeyError, AttributeError):
    #         raise BrokenOvenHandlerError
    #
    # async def get_dish_in_oven(self, oven_id):
    #     try:
    #         oven_object = await self.get_oven_by_id(oven_id)
    #         dish_in_oven = oven_object.dish
    #         return dish_in_oven
    #     except (KeyError, AttributeError):
    #         raise BrokenOvenHandlerError

    async def fetch_oven_list_by_status(self, oven_status):
        """Этот метод получает список печей с необходимым статусом
        :return list of instances OvenUnit class
        [ < api_server.equipment.OvenUnit object at 0x03C74D60 >, < api_server.equipment.OvenUnit object at0x03C74928 >]
        """
        try:
            free_oven_list = [oven for oven in self.oven_units.values() if oven.status == oven_status]
            return free_oven_list
        except RecursionError:
            return None

    async def select_oven_by_status(self, oven_status):
        """Этот метод получает id печи, котрая последняя в списке c нужным статусом
        :return oven_is --> str"""
        free_oven_list = await self.fetch_oven_list_by_status(oven_status="free")
        if not free_oven_list:
            oven_can_be_cleaned = await self.fetch_oven_list_by_status(oven_status="waiting_60")
            if oven_can_be_cleaned:
                free_oven_list = oven_can_be_cleaned
            else:
                print("Какая то супер ошибка, печей нет! Работать не можем")
                raise NoFreeOvenError("Нет свободных печей, не можем работать")
        oven_id = free_oven_list.pop().oven_id
        print("Выбрана печь", oven_id)
        return oven_id

    async def oven_reserve(self, dish_id):
        """Этот метод выбираем 1 доступную печь, меняет статус на reserved и добавляет номер блюда в словарь печи
        :param dish_id: str
        :return instance OvenUnit class
        """
        try:
            print("Запускается резервация оборудования печи")
            oven_id = await self.select_oven_by_status(oven_status="free")
        except NoFreeOvenError:
            print("Какая то супер ошибка, печей нет! Работать не можем Перенесли на уровень выше")
            raise OvenReservationError("Нет свободных печей, не можем работать")
        self.oven_units[oven_id].status = "reserved"
        self.oven_units[oven_id].dish = dish_id
        print("Статус печи изменен")
        return self.oven_units[oven_id]


class OvenUnit(object):
    def __init__(self, oven_data):
        self.oven_id = oven_data["oven_id"]
        self.status = oven_data["status"]
        self.dish = None
        self.stop_baking_time = None
        self.dish_waiting_time = None
        self.dish_liquidation_time = None

    async def get_oven_status(self):
        return self.status

    def __repr__(self):
        return f"Печь № {self.oven_id} {self.status}"


class CutStation(object):
    def __init__(self, equipment_data):
        uuid, status = equipment_data
        self.id = uuid
        self.is_ok = status
        self.is_free = asyncio.Event()
        self.be_free_at = None

    async def set_occupied(self, unix_time=time.time()):
        """
        Этот метод помечает, что станция нарезки занята и освободится
        в секундах с момента epoch.
        :param unix_time: float. The time in seconds since the epoch
        as a floating point number.
        """
        self.is_free.clear()
        self.be_free_at = unix_time

    async def set_free(self):
        """ Этот метод уведомляет всех желающих о том,
        что станция нарезки свободная
        """
        self.is_free.set()
        self.be_free_at = None
