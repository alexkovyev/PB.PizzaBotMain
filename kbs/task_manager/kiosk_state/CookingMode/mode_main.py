import asyncio
import time

from .operations.order_creation_utils import CreateOrder
from .BaseOrder import BaseOrder
from kbs.exceptions import OvenReserveFailed
from kbs.data.kiosk_modes.cooking_mode import CookingModeConst


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
        # wtf? что за лимит
        self.is_limit_active = asyncio.Event()

    @property
    def is_downtime(self):
        """Проверяет можно ли танцеать, те все очереди пустые
        :return bool
        """
        return all(map(lambda p: p.empty(),
                       (self.main_queue, self.low_priority_queue, self.high_priority_queue)))

    async def checking_order_for_double(self, new_order_id):
        """Этот метод проверяет есть ли уже заказ с таким ref id в обработке
        :param new_order_id: str
        :return bool
        """
        return True if new_order_id not in self.current_orders_proceed else False

    async def create_new_order(self, new_order_id):
        """Этот метод создает экземпляр класса Order и
         заносит его в словарь self.current_orders_proceed

        params: new_order_id: str, uuid нового заказа, получаемого в запросе на API

        """

        order_content = await CreateOrder.data_preperaion_for_new_order(new_order_id,
                                                                        self.recipes)
        try:
            ovens_reserved = await CreateOrder.reserve_oven(order_content, self.equipment)
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
        # убрать магическое число
        dish_list = []
        time_from = time.time() + CookingModeConst.DISH_BEFORE_READY_INFORM_TIME
        time_till = time_from + 1
        for oven in self.equipment.ovens.oven_units.values():
            if oven.stop_baking_time is not None and time_from < oven.stop_baking_time < time_till:
                print("Это время окончания выпечки в печи", oven.stop_baking_time)
                print(time.time())
                print("Это блюдо", oven.dish)
                dish_list.append(oven.dish)
                print("записали в список", dish_list)

    async def dish_inform_monitor(self):
        while True:
            time_list = []
            for oven in self.equipment.ovens.oven_units.values():
                if oven.stop_baking_time is not None and oven.stop_baking_time > (time.time() +10) and \
                        oven.stop_baking_time < (time.time() +11):
                    print("Это время окончания выпечки в печи", oven.stop_baking_time)
                    print(time.time())
                    print("Это блюдо", oven.dish)
                    time_list.append(oven.dish)
                    print("записали в список", time_list)
            print("Это временной список для готовности блюда", time_list)
            if time_list:
                for dish in time_list:
                    print("Записываем статус блюда на почти готово", dish)
                    dish_object = await self.get_dish_object(dish)
                    print("Это номер заказа", dish_object.one_dish_order)
                    if dish_object.one_dish_order:
                        print("заказ почти готов", dish_object.order_ref_id)
            await asyncio.sleep(1)

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
                    await self.unpack_chain_data(self.main_queue)
                elif not self.low_priority_queue.empty():
                    print("Моем или выкидываем пиццу")