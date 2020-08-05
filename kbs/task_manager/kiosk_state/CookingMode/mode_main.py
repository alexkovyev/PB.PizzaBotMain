import asyncio
import time

from .cooking_mode_utils import Utils
from .handlers import CookingModeHandlers
from .order import Order
from .operations.order_creation_utils import OrderInitialData
from kbs.exceptions import BrokenOvenHandlerError, OvenReservationError, OvenReserveFailed
from kbs.data.kiosk_modes.cooking_mode import CookingModeConst, Status
from kbs.cntrls_api.ControllerBus import Controllers
from kbs.ra_api.RA import RA


class CookingMode(CookingModeHandlers, Utils):
    """Это основной режим готовки
    self.all_recipes - это словарь, содержащий спарсенные данные рецепта

    self.equipment - это текщий экземпляр класса Equipment

    self.current_orders_proceed - это словарь, содержащий все заказы за текущий сеанс работы

    self.orders_requested_for_delivery - это словарь, содержащий все заказы, по которым поучатель
                                         просканировал qr код

    self.oven_time_changes_event - это словарь, содержащий событие и результат события.
    Результат события - это словарь вида {oven_id: stop_baking_time}

    """

    def __init__(self, recipes, equipment):
        self.all_recipes = recipes
        self.equipment = equipment
        self.current_orders_proceed = {}
        self.orders_requested_for_delivery = {}
        self.oven_time_changes_event = {"event": asyncio.Event(), "result": None}
        # разные полезные очереди по приоритету
        self.main_queue = asyncio.Queue()
        self.high_priority_queue = asyncio.Queue()
        self.low_priority_queue = asyncio.Queue()

    @property
    def is_downtime(self):
        """Проверяет можно ли танцеать, те все очереди пустые
        :return bool
        """
        return all(map(lambda p: p.empty(),
                       (self.main_queue, self.low_priority_queue, self.high_priority_queue)))

    async def checking_order_for_double(self, new_order_id):
        """Этот метод проверяет есть ли уже заказ с таким check_code в обработке
        :param new_order_id: str
        :return bool
        """
        return True if new_order_id not in self.current_orders_proceed else False

    # @staticmethod
    # async def put_chains_in_queue(dish, queue):
    #     """Добавляет чейны рецепта в очередь в виде кортежа (dish, chain)"""
    #     chains = dish.cooking_recipe
    #     for chain in chains:
    #         await queue.put(chain)

    # async def get_dish_object(self, dish_id):
    #     """Этот метод возращает экземпляр класса блюда по заданному ID"""
    #     for order in self.current_orders_proceed.values():
    #         for dish in order.dishes:
    #             if dish.id == dish_id:
    #                 return dish

    # @staticmethod
    # async def change_oven_in_dish(dish_object, new_oven_object):
    #     """ Этот метод переназнаает печь в блюде
    #     :param dish_object: объект блюда
    #     :param new_oven_object: объект печи
    #     :return: dish instance BaseDish class
    #     """
    #     dish_object.oven_unit = new_oven_object

    async def new_order_proceed(self, order):
        """Этот метод совершает действия по обработке заказа после создания"""

        await order.order_marker()
        self.current_orders_proceed[order.check_code] = order
        for dish in order.dishes:
            # переместить назначение пф перед запуском готовки КАК?
            await dish.half_staff_cell_evaluation()
            await self.put_chains_in_queue(dish, self.main_queue)
        await order.create_is_order_ready_monitoring()
        asyncio.create_task(order.order_readiness_monitoring())

    async def create_new_order(self, new_order_check_code):
        """Этот метод создает экземпляр класса Order и
         заносит его в словарь self.current_orders_proceed

        params: new_order_check_code: str, uuid нового заказа, получаемого в запросе на API

        """

        order_content = await OrderInitialData.data_preperation_for_new_order(new_order_check_code,
                                                                              self.all_recipes)
        try:
            ovens_reserved = await OrderInitialData.reserve_oven(order_content,
                                                                 self.equipment)
        except (OvenReservationError, OvenReserveFailed) as e:
            print("Заказ не создан потому что", e)
            return
        order = Order(order_content, ovens_reserved, self.oven_time_changes_event)
        if order:
            # если заказ создан успешно, помещаем его в словарь всех готовящихся заказов
            await self.new_order_proceed(order)
        else:
            print("Заказ не создан")
            pass

    async def stop_baking_time_setter(self):
        """Этот метод обрабатывает данные об изменении времени окончания выпечки
        """
        futura_result = await self.oven_time_changes_event["result"]
        print("ЭТО СРАБОТАЛА ФУТУРА", futura_result)
        for oven in futura_result:
            print(oven)
            lock = asyncio.Lock()
            async with lock:
                self.equipment.ovens.oven_units[oven].stop_baking_time = futura_result[oven]
            print("Это результат сетера", self.equipment.ovens.oven_units[oven].stop_baking_time)

    async def clear_time_changes_monitor(self):
        lock = asyncio.Lock()
        async with lock:
            self.oven_time_changes_event["event"].clear()
            self.oven_time_changes_event["result"] = None

    async def time_changes_waiter(self):
        """Это фоновая задача, работающая во время режима готовки
        Она отслеживает наступление события изменения времени
        выпечки, возврщаемые контроллерами в результате
        операций с печью.
        Необходима для информирование о готовности блюда заранее

        После наступления события и его обработки очищает
        """
        while True:
            await self.oven_time_changes_event["event"].wait()
            print("**:*:?*?*?*?*?%? СРАБОТАЛ event")
            print("Результат", self.oven_time_changes_event["result"])
            await self.stop_baking_time_setter()
            await self.clear_time_changes_monitor()

    async def select_almost_ready_dishes(self):
        dish_list = []
        time_from = time.time() + CookingModeConst.DISH_BEFORE_READY_INFORM_TIME
        time_till = time_from + CookingModeConst.DISH_ALMOST_READY_CHECKING_GAP
        for oven in self.equipment.ovens.oven_units.values():
            if oven.stop_baking_time is not None and time_from < oven.stop_baking_time < time_till:
                print("Это время окончания выпечки в печи", oven.stop_baking_time)
                print(time.time())
                print("Это блюдо", oven.dish)
                dish_list.append(oven.dish)
                print("записали в список", dish_list)
        return dish_list

    async def dish_stop_baking_time_handler(self, dish_list):
        """

        :param dish_list:
        """
        for dish in dish_list:
            print("Записываем статус блюда на почти готово", dish)
            dish_object = await self.get_dish_object(dish)
            print("1 блюдо в заказе?", dish_object.is_last_dish_in_order)
            if dish_object.is_last_dish_in_order:
                print("заказ почти готов", dish_object.order_ref_id)

    async def dish_inform_monitor(self):
        """

        """
        while True:
            dish_list = await self.select_almost_ready_dishes()
            # print("Это временной список для готовности блюда", dish_list)
            if dish_list:
                print("Это временной список для готовности блюда", dish_list)
                await self.dish_stop_baking_time_handler(dish_list)
            await asyncio.sleep(CookingModeConst.DISH_ALMOST_READY_CHECKING_GAP)

    async def run_chain(self, chain_to_do, params=None):
        """Этот метод распаковывает кортеж, проверяет можно ли готовить блюдо
        (те статус блюда не STOP_STATUS) и запускает чейн с параметрами
        Для теста, соуса и добавки params=None
        Для каждого элемента начинки: (method, params)

        """
        if isinstance(chain_to_do, tuple):
            chain_to_do, params = chain_to_do
        if chain_to_do.__self__.status != Status.STOP_STATUS:
            print(f"PBM {time.time()} - Готовим блюдо {chain_to_do.__self__.id}")
            print()
            # print("ЭТО ПАРАМС", params)
            await chain_to_do(params, self.equipment)

    async def qr_code_scanned_handler(self, **kwargs):
        """Этот метод проверяет, есть ли заказ с таким чек кодом в current_orders_proceed.
            Входные данные params: полученный от контроллера словарь с чек кодом заказа и окном выдачи
            "check_code": int, "pickup": int"""
        print(f"PBM {time.time()} Обрабатываем событе QR_CODE")
        print()
        try:
            order_check_code = kwargs["params"]["check_code"]
            pickup_point = kwargs["params"]["pickup"]
            await self.request_delivery_handler(order_check_code,
                                                pickup_point,
                                                self.current_orders_proceed)

        except KeyError:
            print("Ошибка ключа, что делать?")
            return

    async def broken_equipment_handler(self, event_params, equipment):
        await self.broken_hardware_handler(event_params, equipment)

    # async def qr_code_scanned_handler(self, **kwargs):
    #     """Этот метод проверяет, есть ли заказ с таким чек кодом в current_orders_proceed.
    #     Входные данные params: полученный от контроллера словарь с чек кодом заказа и окном выдачи
    #     "check_code": int, "pickup": int"""
    #     print(f"PBM {time.time()} Обрабатываем событе QR_CODE")
    #     print()
    #     try:
    #         order_check_code = kwargs["params"]["check_code"]
    #         pickup_point = kwargs["params"]["pickup"]
    #     except KeyError:
    #         print("Ошибка ключа, что делать?")
    #         return
    #     set_mode_param = await self.evaluation_status_to_set_mode(order_check_code)
    #     print(set_mode_param)
    #     if set_mode_param == "ready":
    #         self.orders_requested_for_delivery[order_check_code] = order_check_code
    #         asyncio.create_task(self.delivery_request_handler(order_check_code))
    #         self.current_orders_proceed[order_check_code].pickup_point = pickup_point
    #         self.current_orders_proceed[order_check_code].delivery_request_event.set()
    #     await Controllers.set_pickup_point_mode(set_mode_param, pickup_point)
    #     # не доделано
    #     # await self.high_priority_queue.put(qr_code_data)
    #
    # async def evaluation_status_to_set_mode(self, order_check_code):
    #     """Передает контроллу значение, на основании которого пользователю
    #     выводится информация о заказе на экране пункта выдачи
    #     переделать на коды см в ноушн
    #     если пицца не готова режим ожидания
    #     """
    #     CNTRLS_SET_MODE_OPTIONS = {1: "not_found",
    #                                2: "in_progress",
    #                                3: "ready",
    #                                4: "стухло"}
    #     OPTIONS = {
    #         "received": 2,
    #         "cooking": 2,
    #         "ready": 3,
    #         "informed": 3,
    #         "failed_to_be_cooked": 3
    #     }
    #     if order_check_code in self.current_orders_proceed:
    #         order_status = self.current_orders_proceed[order_check_code].status
    #         try:
    #             set_mode = CNTRLS_SET_MODE_OPTIONS[OPTIONS[order_status]]
    #         except KeyError:
    #             print("статус блюда не распознан")
    #             set_mode = "not_found"
    #     else:
    #         set_mode = "not_found"
    #     return set_mode
    #
    # async def delivery_request_handler(self, order_check_code):
    #     """Запускает процедуру выдачи заказа
    #     ДОБАВИТЬ ОЧИСТКУ поля ПЕЧЬ после упаковке --> oven_unit = None"""
    #     for dish in self.current_orders_proceed[order_check_code].dishes:
    #         print("Вот это блюдо выдаем", dish)
    #         # не сделано

    async def start(self):
        """Этот метод обеспечивает вызов методов по приготовлению блюд и другой важной работе"""

        asyncio.create_task(self.time_changes_waiter())
        asyncio.create_task(self.dish_inform_monitor())

        while True:
            if self.is_downtime:
                print(f"PBM {time.time()} - Танцуем, других заданий нет")
                print()
                await RA.dance()
            else:
                if not self.high_priority_queue.empty():
                    print(f"PBM {time.time()} - Выдаем заказа")
                    print()
                    await self.high_priority_queue.get()
                elif not self.main_queue.empty():
                    chain_to_do = await self.main_queue.get()
                    await self.run_chain(chain_to_do)
                elif not self.low_priority_queue.empty():
                    print("Моем или выкидываем пиццу")
