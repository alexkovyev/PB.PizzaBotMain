"""Это базовый класс режима работы
не доделано
"""

class BaseMode(object):
    def __init__(self):
        self.is_busy = False

    async def broken_equipment_handler(self, event_params, equipment):
        BROKEN_STATUS = "broken"
        try:
            unit_type = event_params["unit_type"]
            unit_id = event_params["unit_name"]
        except KeyError:
            print("Не найден ключ в событии")
        print("Это тип оборудования", unit_type)
        try:
            if unit_type != "ovens":
                print("Меняем данные оборудования")
                print(getattr(equipment, unit_type))
                getattr(equipment, unit_type)[unit_id] = False
                print("Это оборудование после обработки", getattr(equipment, unit_type))
            else:
                print("Меняем данные печи")
                equipment.ovens.oven_units[unit_id].status = BROKEN_STATUS
        except KeyError:
            print("Ошибка данных оборудования")

    async def qr_code_scanned_handler(self, **kwargs):
        print("Сработало событие сканирования qr кода в режиме неготовки")
        print(kwargs)
        pass

    async def unit_washing_request(self, **kwargs):
        print("Получен запрос на помывку оборудования")
        print(kwargs)
        pass

    def is_ok_to_del(self):
        return True if not self.is_busy else False
