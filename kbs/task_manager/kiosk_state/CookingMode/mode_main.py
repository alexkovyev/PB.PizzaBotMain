import asyncio
import time

from .base_order import BaseOrder
from .operations.order_creation_utils import OrderInitialData
from kbs.exceptions import OvenReserveFailed, BrokenOvenHandlerError
from kbs.data.kiosk_modes.cooking_mode import CookingModeConst
from kbs.ra_api.RA import RA


class CookingMode(object):
    """Это основной режим готовки
    self.recipes - это словарь, содержащий спарсенные данные рецепта

    self.equipment - это текщий экземпляр класса Equipment

    self.current_orders_proceed - это словарь, содержащий все заказы за текущий сеанс работы

    self.orders_requested_for_delivery - это словарь, содержащий все заказы, по которым поучатель
                                         просканировал qr код
    """

    STOP_STATUS = "failed_to_be_cooked"

    def __init__(self, recipes, equipment):
        self.recipes = recipes
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

    @staticmethod
    async def put_chains_in_queue(dish, queue):
        """Добавляет чейны рецепта в очередь в виде кортежа (dish, chain)"""
        chains = dish.chain_list
        for chain in chains:
            await queue.put(chain)

    async def get_dish_object(self, dish_id):
        """Этот метод возращает экземпляр класса блюда по заданному ID"""
        for order in self.current_orders_proceed.values():
            for dish in order.dishes:
                if dish.id == dish_id:
                    return dish

    @staticmethod
    async def change_oven_in_dish(dish_object, new_oven_object):
        """ Этот метод переназнаает печь в блюде
        :param dish_object: объект блюда
        :param new_oven_object: объект печи
        :return: dish instance BaseDish class
        """
        dish_object.oven_unit = new_oven_object


    async def create_new_order(self, new_order_id):
        """Этот метод создает экземпляр класса Order и
         заносит его в словарь self.current_orders_proceed

        params: new_order_id: str, uuid нового заказа, получаемого в запросе на API

        """

        order_content = await OrderInitialData.data_preperaion_for_new_order(new_order_id, self.recipes)
        try:
            ovens_reserved = await OrderInitialData.reserve_oven(order_content, self.equipment)
        except OvenReserveFailed:
            pass
        order = BaseOrder(order_content, ovens_reserved, self.oven_time_changes_event)
        if order:
            # если заказ создан успешно, помещаем его в словарь всех готовящихся заказов
            await order.dish_marker()
            self.current_orders_proceed[order.ref_id] = order
            for dish in order.dishes:
                # переместить назначение пф перед запуском готовки КАК?
                await dish.half_staff_cell_evaluation()
                await self.put_chains_in_queue(dish, self.main_queue)
            await order.create_is_order_ready_monitoring()
            asyncio.create_task(order.order_readiness_monitoring())

    async def stop_baking_time_setter(self):
        """Этот метод обрабатывает данные об изменении времени окончания выпечки
        """
        futura_result = await self.oven_time_changes_event["result"]
        print(futura_result)
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
            # lock = asyncio.Lock()
            # async with lock:
            #     self.oven_time_changes_event["event"].clear()
            #     self.oven_time_changes_event["result"] = None

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
            print("Это номер заказа", dish_object.one_dish_order)
            if dish_object.one_dish_order:
                print("заказ почти готов", dish_object.order_ref_id)

    async def dish_inform_monitor(self):
        """

        """
        while True:
            dish_list = await self.select_almost_ready_dishes()
            print("Это временной список для готовности блюда", dish_list)
            if dish_list:
                await self.dish_stop_baking_time_handler(dish_list)
            await asyncio.sleep(CookingModeConst.DISH_ALMOST_READY_CHECKING_GAP)

    async def run_chain(self, chain_to_do, params=None):
        """Этот метод распаковывает кортеж, проверяет можно ли готовить блюдо
        (те статус блюда не STOP_STATUS) и запускает чейн с параметрами """
        print("Начинаем распаковку")
        if isinstance(chain_to_do, tuple):
            chain_to_do, params = chain_to_do
        if chain_to_do.__self__.status != self.STOP_STATUS:
            print("Готовим блюдо", chain_to_do.__self__.id)
            await chain_to_do(params, self)

    async def broken_oven_handler(self, unit_id):
        try:
            broken_oven_object = await self.equipment.ovens.get_oven_by_id(unit_id)
            if broken_oven_object.status != "free":
                print("Сломавшаяся печь со статусом", broken_oven_object.status)
                dish_id_in_broken_oven = broken_oven_object.dish
                dish_object_in_broken_oven = await self.get_dish_object(dish_id_in_broken_oven)
                print("Блюдо в сломавгейя печи со статусом", dish_object_in_broken_oven.status)
                new_oven_object = await self.equipment.ovens.oven_reserve(dish_id_in_broken_oven)
                if broken_oven_object.status == "reserved":
                    broken_oven_object.dish = None
                    await self.change_oven_in_dish(dish_object_in_broken_oven, new_oven_object)
                elif broken_oven_object.status == "occupied":
                    if dish_object_in_broken_oven.status == "cooking":
                        print("Запутить смену лопаток в высокий приоритет")
                        # await self.high_priority_queue.put((Recipy.switch_vane_cut_oven, (new_oven_object.oven_id,
                        #                                                                   broken_oven_id)))
                        # блюдо в печи не стирается пока не выполнится смена
                    elif dish_object_in_broken_oven.status == "baking":
                        print("Запустить ликвидацю блюда")
                        # await self.low_priority_queue.put(dish_object.throwing_away_chain_list)
                elif broken_oven_object.status == "waiting_15" or "waiting_60":
                        # не сделано
                        pass
            broken_oven_object.status = "broken"
            print("Мы обработали печь в cooking")
            for oven in self.equipment.ovens.oven_units:
                print(self.equipment.ovens.oven_units[oven])

        except (BrokenOvenHandlerError, AttributeError):
            pass

    async def broken_equipment_handler(self, event_params, equipment):
        """Этот метод обрабатывает поломки оборудования, поступающий на event_listener
        :param event_params: dict вида {unit_type: str, unit_id: uuid}
        """
        print("Обрабатываем уведомление об поломке оборудования", time.time())
        print(event_params)
        unit_type = event_params["unit_type"]
        unit_id = event_params["unit_name"]
        try:
            if unit_type != "ovens":
                print("Меняем данные оборудования")
                getattr(equipment, unit_type)[unit_id] = False
            else:
                print("Меняем данные печи из cooking")
                await self.broken_oven_handler(unit_id)
        except KeyError:
            print("Ошибка данных оборудования")

    async def qr_code_scanned_handler(self, **kwargs):
        print("Сработало событие сканирования qr кода в режиме неготовки")
        print("Данные евента qr кода", kwargs)
        pass

    async def start(self):
        """Этот метод обеспечивает вызов методов по приготовлению блюд и другой важной работе"""

        asyncio.create_task(self.time_changes_waiter())
        asyncio.create_task(self.dish_inform_monitor())

        while True:
            print("Работает cooking", time.time())
            if self.is_downtime:
                print("Танцуем, других заданий нет")
                await RA.dance()
            else:
                if not self.high_priority_queue.empty():
                    print("Выдаем заказ")
                    await self.high_priority_queue.get()
                elif not self.main_queue.empty():
                    print("Вернулись в очередь main")
                    chain_to_do = await self.main_queue.get()
                    await self.run_chain(chain_to_do)
                elif not self.low_priority_queue.empty():
                    print("Моем или выкидываем пиццу")