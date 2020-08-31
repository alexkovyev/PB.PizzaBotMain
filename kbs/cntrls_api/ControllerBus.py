"""Это служебный модуль, имитирующий API контроллеров
Написан для тестов работоспособности по-черному :) """


import asyncio
import random
import time

from pydispatch import Dispatcher


"""PBM использует следующие методы и объекты контроллеров:
1. экземпляр класса ControllersEvents events_monitoring
2. методы класса Controller:
   - give_dough
   - give_sauce
   - cut_the_product
   - start_baking Общий метод для работы с печами для операций:
    а) прогрев печи
    б) выпечка
    в) подогрев
    г) корочкообразование
   - give_paper
   - inform_order_is_delivered
   - send_message_qr
"""


class ControllersEvents(Dispatcher):
    """ Это внутренний метод контроллеров
    Dispatcher for controller event handlers. DON'T CREATE instances of this class, use
    events_monitoring.
    """
    _events_ = ['qr_scanned', 'hardware_status_changed', 'equipment_washing_request']

    def qr_scanned(self, params):
        self.emit('qr_scanned', params=params)

    def hardware_status_changed(self, unit_type,  unit_name):
        self.emit('hardware_status_changed', unit_type=unit_type, unit_name=unit_name)

    def request_for_wash(self, unit_name):
        self.emit('equipment_washing_request', unit_name=unit_name)


cntrls_events = ControllersEvents()


async def event_generator(cntrls_events, equipment):
    """ PBM подписывается на следующие уведомления:
    - сканирование qr-code
    - изменение статуса следующего оборудования: печи, станция нарезки, узел упаковки, соусо-поливательная станция,
    окна выдачи.
    - необходимость провести мойку по причине накопления колво выполненных циклов
    Описание события см в описании метода
    """

    async def qr_code_scanning_alarm(cntrls_events, *args):
        """ В теле уведомления (params) в словаре необходимо указать следующие данные
        (пары key:value с аннотацией типов)
        - "check_code": str,  value: str
        - "pickup": str, value: uuid4 str
        Идентификатор оборудования должен быть единым для всех элементов системы. """
        print(f"CBUS {time.time()} Сработало событие QR-CODE")
        print()
        params = {"check_code": 11, "pickup": 1}
        cntrls_events.qr_scanned(params)

    async def hardware_status_changed(cntrls_events, equipment):
        """ {"equipment_type": cut_station, "uuid": o48932492834281}
        Приходят только уведомления о поломке, возобнавление работы через "оператора и перезагрузку"
        """
        print(f"CBUS {time.time()} Сработало событие поломка оборудования")
        data = {
            "cut_station": {"f50ec0b7-f960-400d-91f0-c42a6d44e3d0": True},
            "package_station": {"afeb1c10-83ef-4194-9821-491fcf0aa52b": True},
            "sauce_dispensers": {"16ffcee8-2130-4a2f-b71d-469ee65d42d0": True,
                                 "ab5065e3-93aa-4313-869e-50a959458439": True,
                                 "28cc0239-2e35-4ccd-9fcd-be2155e4fcbe": True,
                                 "1b1af602-b70f-42a3-8b5d-3112dcf82c26": True,
                                 },
            "dough_dispensers": {"ebf29d04-023c-4141-acbe-055a19a79afe": True,
                                 "2e84d0fd-a71f-4988-8eee-d0373c0bc609": True,
                                 "68ec7c16-f57b-43c0-b708-dfaea5c2e1dd": True,
                                 "75355f3c-bf05-405d-98af-f04bcba7d7e4": True,
                                 },
            "pick_up_points": {"1431f373-d036-4e0f-b059-70acd6bd18b9": True,
                               "b7f96101-564f-4203-8109-014c94790978": True,
                               "73b194e1-5926-45be-99ec-25e1021b96f7": True,
                               }
        }
        unit_type = random.choice(["ovens"])
        # unit_type = random.choice(["ovens", "cut_station", "package_station", "sauce_dispensers"])
        if unit_type != "ovens":
            unit_id = random.choice(list(data[unit_type].keys()))
        else:
            unit_id = random.choice(list(equipment.ovens.oven_units.keys()))
        print("сломалось", unit_type, unit_id)
        print()
        cntrls_events.hardware_status_changed(unit_type, unit_id)

    async def equipment_washing_request(cntrls_events, *args):
        """Информирует о том, что необходимо провести мойку такого то оборудования"""
        print(f"CBUS {time.time()} Нужно помыть оборудование")
        unit_name = "cut_station"
        cntrls_events.request_for_wash(unit_name)

    while True:
        # это эмуляция работы контроллеров по генерации разных событий
        # Используется PBM для тестирования
        options = [qr_code_scanning_alarm, hardware_status_changed, equipment_washing_request]
        my_choice = random.randint(0, 2)
        what_happened = options[my_choice]
        await what_happened(cntrls_events, equipment)
        n = random.randint(10, 20)
        # print(f"Trouble-maker засыпает на {n} сек в {time.time()}")
        await asyncio.sleep(n)
        # print("Trouble-maker снова с нами", time.time())


class Movement(object):
    """Это эмуляция работы контроллеров в части засыпания при выполнении методов :) Используется PBM
    для тестирования"""

    @staticmethod
    async def movement(*args):
        # n = random.randint(2, 5)
        n = 10
        await asyncio.sleep(n)
        result = random.choice([True, True])
        return result


class Dough(Movement):

    @classmethod
    async def give(cls, dough_point):
        """Метод обеспечивает выдачу теста
        :param dough_point: uuid4 str
        :return bool
        """
        print(f"CNTRS {time.time()} Выдаем тесто из тестовой станции № {dough_point}")
        print()
        result = await cls.movement(dough_point)
        print(f"CNTRS {time.time()} Выдали тесто из тестовой станции № {dough_point}")
        print()
        return result


class CutTable(Movement):

    @classmethod
    async def sauce(cls, sauce_recipe):
        """Метод обеспечивает поливание соусом
        :param sauce_recipe: list [(tuple), (tuple)]
        для вложенного кортежа: 0 - id насосной станции uuid str, 1 - программа поливки int
        поменять на list [(tuple), (tuple)]
        0 - номер программы поливки →int,
        1 - id насосной станции uuid → str.
        :return bool
        """
        print(f"CNTRS {time.time()} Поливаем соусом {sauce_recipe}")
        print()
        result = await cls.movement()
        print(f"CNTRS {time.time()} Закончили поливать соусом {sauce_recipe}")
        print()
        return result

    @classmethod
    async def cut(cls, cutting_program):
        """Метод обеспечивает нарезку продукта
        :param cutting_program: int
        :return bool
        """
        print(f"CNTRS {time.time()} Начинаем нарезку пф {cutting_program}")
        print()
        result = await cls.movement()
        print(f"CNTRS {time.time()} Закончили нарезку пф {cutting_program}")
        print()
        return result


class Oven():

    @classmethod
    async def bake(cls, oven_unit, program,
                           time_changes_requset):
        """Запускает выпечку в конкртеной печи
        :param oven_unit: uuid4
               program: int
               time_changes_request: future object
        :return
               sets data in time_changes_request {oven_id: unix_time} для всех печей, время которых изменилось
               result: bool or raise OvenError
         """
        print(program)
        if program == 1:
            oven_mode = "разогрев печи"
            print("Начинаем", oven_mode, "в", oven_unit, time.time())
            time_changes_requset.set_result({})
            await asyncio.sleep(15)
            print("контроллеры закончили", oven_mode, time.time())
            return True
        elif program == 2:
            oven_mode = "выпечка"
            print("Начинаем", oven_mode, "в", oven_unit, time.time())
            time_changes_requset.set_result({oven_unit: (time.time() + 60)})
            await asyncio.sleep(60)
        elif program == 3:
            oven_mode = "корочкообразование"
            print("Начинаем", oven_mode, "в", oven_unit, time.time())
            time_changes_requset.set_result({})
            await asyncio.sleep(30)

        print("контроллеры закончили", oven_mode, time.time())
        return True

    @staticmethod
    async def turn_off():
        pass


class Paper(Movement):

    @classmethod
    async def give(cls):
        """Метод выдает бумагу в станции упаковки
        без параметров) """
        print("Выдаем упаковку", time.time())
        result = await cls.movement()
        print("контроллеры закончили выдавать бумагу", time.time())
        return result


class Dispenser(Movement):

    @classmethod
    async def unknown_code(cls, pick_up_point):
        """Метод выставляет режим работы пункта выдачи"""
        return True

    @classmethod
    async def not_ready(cls, pick_up_point):
        """Метод выставляет режим работы пункта выдачи"""
        return True

    @classmethod
    async def out_of_time(cls, pick_up_point):
        """Метод выставляет режим работы пункта выдачи"""
        return True

    @classmethod
    async def ready(cls, pick_up_point):
        """Метод выставляет режим работы пункта выдачи"""
        return True

    @classmethod
    async def dispense(cls):
        """Метод запускает процедуру выдачи заказа и уведомления о том, получен ли заказ"""
        pass


class Controllers(Movement):

    def __init__(self):
        self.cntrls_events = ControllersEvents()
        self.dough = Dough()
        self.cut_table = CutTable()
        self.oven = Oven()
        self.dispenser = Dispenser()
