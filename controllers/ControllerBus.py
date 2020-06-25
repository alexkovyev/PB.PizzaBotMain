import asyncio
import random
import time

from pydispatch import Dispatcher

"""PBM использует следующие методы и объекты контроллеров:
1. экземпляр класса ControllersEvents cntrls_events
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
    cntrls_events.
    """
    _events_ = ['qr_scanned', 'hardware_status_changed', 'equipment_washing_request']

    def qr_scanned(self, _params):
        self.emit('qr_scanned', params=_params)

    def hardware_status_changed(self, _unit_name, _status):
        self.emit('hardware_status_changed', unit_name=_unit_name, status=_status)

    def request_for_wash(self, _unit_name):
        self.emit('equipment_washing_request', unit_name=_unit_name)


cntrls_events = ControllersEvents()


async def event_generator(cntrls_events):
    """ PBM подписывается на следующие уведомления:
    - сканирование qr-code
    - изменение статуса следующего оборудования: печи, станция нарезки, узел упаковки, соусо-поливательная станция,
    окна выдачи. АРСЕНИЙ! если будет еще оборудование, добавь пжста
    - необходимость провести мойку по причине накопления колво выполненных циклов
    Описание события см в описании метода
    """

    async def qr_code_scanning_alarm(cntrls_events):
        """ В теле уведомления (params) в словаре необходимо указать следующие данные
        (пары key:value с аннотацией типов)
        - "check_code": str,  value: str
        - "pickup": str, value: uuid4 str
        Идентификатор оборудования должен быть единым для всех элементов системы. """
        print("Сработало событие qr код", time.time())
        params = {"ref_id": 65, "pickup": 1}
        cntrls_events.qr_scanned(params)

    async def hardware_status_changed(cntrls_events):
        """ ВОПРОС ТРЕБУЕТ ОТВЕТА к контроллерам: по идее тут все оборудование. Вы просто выдаете идентификатор и статус
        или будет еще тип: "oven", "cut_station", те {"equipment_type": cut_station,
                                                      "uuid": o48932492834281,
                                                       "status": "broken"}
        Приходят только уведомления о поломке, возобнавление работы через "оператора и перезагрузку"
        """
        print("Сработало событие ПОЛОМКА ПЕЧИ", time.time())
        cntrls_events.hardware_status_changed('21', 'broken')

    async def equipment_washing_request(cntrls_events):
        """Информирует о том, что необходимо провести мойку такого то оборудования"""
        print("Нужно помыть оборудование", time.time())
        _unit_name = "cut_station"
        cntrls_events.request_for_wash(_unit_name)

    while True:
        # это эмуляция работы контроллеров по генерации разных событий
        # Используется PBM для тестирования
        await asyncio.sleep(2)
        print("Выбираем событие", time.time())
        options = [qr_code_scanning_alarm, hardware_status_changed, equipment_washing_request]
        my_choice = random.randint(0, 2)
        what_happened = options[my_choice]
        await what_happened(cntrls_events)
        n = random.randint(20, 40)
        print(f"Trouble-maker засыпает на {n} сек в {time.time()}")
        await asyncio.sleep(n)
        print("Trouble-maker снова с нами", time.time())


class Movement(object):
    """Это эмуляция работы контроллеров в части засыпания при выполнении методов :) Используется PBM
    для тестирования"""

    @staticmethod
    async def movement(*args):
        n = random.randint(2, 5)
        print("-- Время работы контроллеров", n)
        await asyncio.sleep(n)
        result = random.choice([True, True, True])
        print("-- Метод контроллеров завершен")
        return result


class Controllers(Movement):

    @classmethod
    async def give_dough(cls, dough_point):
        """Метод обеспечивает выдачу теста
        :param dough_point: uuid4 str
        :return bool
        """
        print("Выдаем тесто из тестовой станции №", dough_point)
        result = await cls.movement(dough_point)
        return result

    @classmethod
    async def give_sauce(cls, sauce_recipe):
        """Метод обеспечивает поливание соусом
        :param sauce_recipe: list [(), ()]
        для вложенного кортежа: 0 - id насосной станции uuid str, 1 - программа поливки int
        :return bool
        """
        print("Поливаем соусом")
        print("Параметры из контроллеров считались", sauce_recipe)
        result = await cls.movement()
        return result

    @classmethod
    async def cut_the_product(cls, cutting_program):
        """Метод обеспечивает нарезку продукта
        :param cutting_program: int
        :return bool
        """
        print("Начинаем резать продукт")
        result = await cls.movement()
        return result

    @classmethod
    async def start_baking(cls, oven_unit, oven_mode, program, time_changes_requset):
        """Запускает выпечку в конкртеной печи
        :param oven_unit: uuid4
               oven_mode: str
               program: int
               time_changes_request: futura object
        oven_mode options:
        - "pre_heating"
        - "baking"
        - "stand_by"
        - "make_crust"
        :return
               sets data in time_changes_request {oven_id: unix_time} для всех печей, время которых изменилось
               result: bool or raise OvenError
         """
        print("Начинаем",oven_mode, "в", oven_unit, time.time())
        if oven_mode == "pre_heating":
            time_changes_requset.set_result({oven_unit: (time.time() + 10)})
            await asyncio.sleep(10)
        else:
            time_changes_requset.set_result({oven_unit: (time.time() + 60)})
            await asyncio.sleep(60)
        result = True
        print("контроллеры закончили", oven_mode, time.time())
        return result

    @classmethod
    async def give_paper(cls):
        """Метод выдает бумагу в станции упаковки
        без параметров) """
        print("Выдаем упаковку", time.time())
        result = await cls.movement()
        print("контроллеры закончили выдавать бумагу", time.time())
        return result

    @classmethod
    async def set_pickup_point_mode(cls, mode, pick_up_point):
        """Метод выставляет режим работы пункта выдачи"""
        return True

    @classmethod
    async def deliver_order(cls):
        """Метод запускает процедуру выдачи заказа и уведомления о том, получен ли заказ"""
        pass

