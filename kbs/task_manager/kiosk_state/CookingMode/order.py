import asyncio
import time

from .dish import Dish
from kbs.data.kiosk_modes.cooking_mode import CookingModeConst


class Order(object):
    """Этот класс содержит информцию о заказе.
    self.check_code: str

    self.dishes: list вида [экземпляр_1_класса_Dish, экземпляр_2_класса_Dish]

    # переделать на константы
    self.status: str


    """

    ORDER_STATUS = ["received", "cooking", "ready", "packed", "wait to delivery", "delivered", "closed",
                    "failed_to_be_cooked", "not_delivered"]

    def __init__(self, new_order_content, ovens_reserved, time_changes_event):

        self.check_code = new_order_content["check_code"]
        self.dishes = self.dish_creation(new_order_content["dishes"], ovens_reserved, time_changes_event)
        self.status = "received"
        # перенести в блюдо
        self.pickup_point = None
        self.dish_readiness_events = []
        self.delivery_request_event = asyncio.Event()

    def dish_creation(self, dishes, ovens_reserved, time_changes_event):
        """Creates list of dishes objects in order

        :param dishes: dict вида {dish_id: {добавить словарь}}
        :param ovens_reserved: list вида [экземпляр_класса_OvenUnit]
        :param time_changes_event: dict вида {"event": asyncio.Event(), "result": None}

        """

        self.dishes = [Dish(time_changes_event, dish_id, dishes[dish_id], self.check_code,
                            ovens_reserved[index]) for index, dish_id in enumerate(dishes)]
        return self.dishes

    async def order_marker(self):
        """Этот метод маркирует заказ в зависимости от кол-ва блюд в нем """
        if len(self.dishes) > 1:
            self.dishes[-1].is_last_dish_in_order = True
        else:
            self.dishes[0].is_last_dish_in_order = True

    async def set_waiting_timer(self):
        print("Начинаем ждать выдачу блюда, 1", time.time())
        stop_time = time.time() + CookingModeConst.OVEN_FREE_WAITING_TIME
        while time.time() < stop_time:
            if not self.delivery_request_event.is_set():
                await asyncio.sleep(1)
                print("Ждем 1 интервал")
            else:
                print("Блюдо запрошено к доставке")
                break
        if not self.delivery_request_event.is_set():
            print("Закончили ждать 1 интервал", time.time())
            for dish in self.dishes:
                dish.oven_unit.status = "waiting_60"
            stop_time = time.time() + CookingModeConst.OVEN_FREE_WAITING_TIME * 2
            while not self.delivery_request_event.is_set() and time.time() < stop_time:
                print("Ждем 2 интервал")
                await asyncio.sleep(1)
            print("ТАЙМЕР закончился, блюдо выкидываем")
        else:
            pass

    async def create_is_order_ready_monitoring(self):
        """Этот метод создает мониторинг готовности блюд заказа через asyncio.Event """
        for dish in self.dishes:
            is_dish_ready_event = asyncio.Event()
            dish.is_dish_ready = is_dish_ready_event
            self.dish_readiness_events.append(is_dish_ready_event)
        return self.dish_readiness_events

    async def order_readiness_monitoring(self):
        """Этот метод проверяет, сработали ли события готовности блюд в заказе"""
        while not all(list(map(lambda i: i.is_set(), self.dish_readiness_events))):
            await asyncio.sleep(1)
        print("Сработало событие ЗАКАЗ ГОТОВ", time.time())
        print(list(map((lambda i: i.status == "failed_to_be_cooked"), self.dishes)))

        await self.change_order_status()
        print("Это статус ЗАКАЗА", self.status)
        await self.set_waiting_timer()
        # записать в БД статус

    async def change_order_status(self):
        if all(list(map((lambda i: i.status == "failed_to_be_cooked"), self.dishes))):
            self.status = "failed_to_be_cooked"
        elif any(list(map((lambda i: i.status == "failed_to_be_cooked"), self.dishes))):
            self.status = "partially_ready"
        else:
            self.status = "ready"

    def __repr__(self):
        return f"Заказ № {self.check_code}"
