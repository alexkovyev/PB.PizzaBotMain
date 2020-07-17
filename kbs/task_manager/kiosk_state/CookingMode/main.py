import asyncio
import time

from .operations.order_creation_utils import CreateOrder
from .BaseOrder import BaseOrder
from kbs.exceptions import OvenReserveFailed


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
                await dish.half_staff_cell_evaluation()
                await self.put_chains_in_queue(dish, self.main_queue)
            await order.create_is_order_ready_monitoring()
            asyncio.create_task(order.order_readiness_monitoring())
