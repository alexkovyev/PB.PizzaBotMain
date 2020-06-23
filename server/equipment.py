"""Этот модуль содержит информацию об оборудовании"""
import asyncio
import time


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
    OVEN_STATUSES = ["broken", "free", "reserved", "occupied", "short_stand_by", "long_stand_by"]

    def __init__(self, equipment_data):
        self.oven_available = Oven(equipment_data["ovens"])
        self.cut_station = equipment_data["cut_station"]
        self.package_station = equipment_data["package_station"]
        self.sauce_dispensers = equipment_data["sauce_dispensers"]
        self.dough_dispensers = equipment_data["dough_dispensers"]
        self.pick_up_points = equipment_data["pick_up_points"]
        print("Данные о печах выглядят так", self.oven_available)


class Oven(object):
    def __init__(self, ovens_data):
        # self.oven_units = ovens_data
        # {'e0714152-182a-4da0-9d06-5190ad44d919': <server.equipment.OvenUnit object at 0x03C74D60>}
        self.oven_units = {i: OvenUnit(ovens_data[i]) for i in ovens_data}
        print("Это объекты печи юниты", self.oven_units)

    # def fetch_free_oven_list(self):
    #     """Этот метод получает список печей со статусом свободны"""
    #     free_oven = [oven for oven in self.oven_units.values() if oven["status"] == "free"]
    #     return free_oven

    def fetch_free_oven_list(self):
        """Этот метод получает список печей со статусом свободны"""
        free_oven = [oven for oven in self.oven_units.values() if oven.status == "free"]
        # тут список объектов
        # [ < server.equipment.OvenUnit object at 0x03C74D60 >, < server.equipment.OvenUnit object at0x03C74928 >]
        print("Это свободная печь", free_oven)
        return free_oven

    # def is_able_to_cook(self):
    #     """Определяет, можно ли готовить на основе того, исправно ли оборудование
    #     учитывает ли это, сколько печей свободно и если их 0.
    #     Если у нас 1 работающая печь киоск все равно работает, или нет?"""
    #     operate_oven_qt = self.fetch_free_oven_list()
    #     # как то проверяем, работают ли узлы выдачи
    #     equipment_status = True if self.is_cut_station_ok and \
    #                                self.is_package_station_ok and \
    #                                len(operate_oven_qt) > 1 \
    #         else False
    #     return equipment_status

    # def get_first_free_oven(self):
    #     """Этот метод получает id печи, котрая последняя в списке свободных"""
    #     free_oven_list = self.fetch_free_oven_list()
    #     if free_oven_list:
    #         oven_id = free_oven_list.pop()["oven_id"]
    #         print("Выбрана печь", oven_id)
    #     else:
    #         print("Нет свободных печей")
    #         # нужно добавить обработчик что делать если блюда 2 а печь свободная 1 шт
    #     return oven_id

    def get_first_free_oven(self):
        """Этот метод получает id печи, котрая последняя в списке свободных"""
        free_oven_list = self.fetch_free_oven_list()
        if free_oven_list:
            oven_id = free_oven_list.pop().oven_id
            print("Выбрана печь", oven_id)
        else:
            print("Нет свободных печей")
            # нужно добавить обработчик что делать если блюда 2 а печь свободная 1 шт
        return oven_id

    # def oven_reserve(self, dish_id):
    #     oven_id = self.get_first_free_oven()
    #     self.oven_units[oven_id]["status"] = "reserved"
    #     self.oven_units[oven_id]["dish"] = dish_id
    #     print("Статус изменен")
    #     return oven_id

    def oven_reserve(self, dish_id):
        oven_id = self.get_first_free_oven()
        self.oven_units[oven_id].status = "reserved"
        print(self.oven_units[oven_id].status)
        self.oven_units[oven_id].dish = dish_id
        print("Статус изменен")
        # return oven_id
        print("Возвращаем объект, а не номер печи", self.oven_units[oven_id])
        return self.oven_units[oven_id]

    # async def oven_broke_handler(self, event_data):
    #     """Это группа функций обрабатывает поломку печи.
    #     - поиск назначенных блюд на печь
    #     - замена печи на исправную
    #     - смена статуса, запись в БД ? Или это контролер делает?
    #     """
    #     print("Обрабатываем уведомление об оборудовании", event_data)
    #     oven_id = int(event_data["unit_name"])
    #     oven_status = event_data["status"]
    #     if self.oven_units[oven_id]["status"] == "reserved":
    #         print("Нужно переназначить печь")
    #         print("Перезначаем блюдо", self.oven_units[oven_id]["dish"])
    #         # new_oven_id = self.get_first_free_oven()
    #     self.oven_units[oven_id]["status"] = oven_status
    #     print("Мы обработали печь")
    #     print("Вот такие печи", self.oven_units)

    async def oven_broke_handler(self, event_data):
        """Это группа функций обрабатывает поломку печи.
        - поиск назначенных блюд на печь
        - замена печи на исправную
        - смена статуса, запись в БД ? Или это контролер делает?
        """
        print("Обрабатываем уведомление об оборудовании", event_data)
        oven_id = int(event_data["unit_name"])
        oven_status = event_data["status"]
        if self.oven_units[oven_id].status == "reserved":
            print("Нужно переназначить печь")
            print("Перезначаем блюдо", self.oven_units[oven_id].dish)
            # new_oven_id = self.get_first_free_oven()
        self.oven_units[oven_id].status = oven_status
        print("Мы обработали печь")
        print("Вот такие печи", self.oven_units)


class OvenUnit(object):
    def __init__(self, oven_data):
        self.oven_id = oven_data["oven_id"]
        self.status = oven_data["status"]
        self.dish = None
        self.stop_baking_time = None
        self.dish_waiting_time = None
        self.dish_liquidation_time = None

    def __repr__(self):
        return f"Печь № {self.oven_id}"
