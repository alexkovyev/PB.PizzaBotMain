"""Этот модуль содержит информацию об оборудовании"""
import asyncio
import time

from server.custom_errors import NoFreeOvenError, OvenReservationError


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
        self.ovens = Oven(equipment_data["ovens"])
        self.cut_station = equipment_data["cut_station"]
        self.package_station = equipment_data["package_station"]
        self.sauce_dispensers = equipment_data["sauce_dispensers"]
        self.dough_dispensers = equipment_data["dough_dispensers"]
        self.pick_up_points = equipment_data["pick_up_points"]


class Oven(object):
    def __init__(self, ovens_data):
        # self.oven_units = ovens_data
        # {'e0714152-182a-4da0-9d06-5190ad44d919': <server.equipment.OvenUnit object at 0x03C74D60>}
        self.oven_units = {i: OvenUnit(ovens_data[i]) for i in ovens_data}

    async def fetch_oven_list_by_status(self, oven_status):
        """Этот метод получает список печей с необходимым статусом
        :return list of instances OvenUnit class
        [ < server.equipment.OvenUnit object at 0x03C74D60 >, < server.equipment.OvenUnit object at0x03C74928 >]
        """
        free_oven_list = [oven for oven in self.oven_units.values() if oven.status == oven_status]
        return free_oven_list

    async def select_oven_by_status(self, oven_status):
        """Этот метод получает id печи, котрая последняя в списке c нужным статусом
        :return oven_is --> str"""
        free_oven_list = await self.fetch_oven_list_by_status(oven_status="free")
        if not free_oven_list:
            oven_can_be_cleaned = await self.select_oven_by_status("waiting_60")
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

    def __repr__(self):
        return f"Печь № {self.oven_id} {self.status}"
