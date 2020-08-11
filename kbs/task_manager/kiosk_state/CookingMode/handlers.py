""" Тут будет описание """

import time

from .cooking_mode_utils import Utils
from kbs.cntrls_api.ControllerBus import Controllers
from kbs.exceptions import BrokenOvenHandlerError


class BrokenEquipmentHandler(Utils):
    async def broken_hardware_handler(self, event_params, equipment):
        """Этот метод обрабатывает поломки оборудования, поступающий на event_listener
        :param event_params: dict вида {unit_type: str, unit_id: uuid}
        :param equipment: instance Equipment class
        """
        print(f"PBM {time.time()} Обрабатываем уведомление об поломке оборудования")
        print(event_params)
        unit_type = event_params["unit_type"]
        unit_id = event_params["unit_name"]
        try:
            if unit_type != "ovens":
                getattr(equipment, unit_type)[unit_id] = False
            else:
                await self.broken_oven_handler(unit_id, equipment)
        except KeyError:
            print("Ошибка данных оборудования")

    async def broken_oven_handler(self, unit_id, equipment):
        """

        :param unit_id:
        :param equipment:
        """
        try:
            broken_oven_object = await equipment.ovens.get_oven_by_id(unit_id)
            if broken_oven_object.status != "free":
                print(f"PBM {time.time()} - Сломавшаяся печь со статусом {broken_oven_object.status}")
                dish_id_in_broken_oven = broken_oven_object.dish
                dish_object_in_broken_oven = await self.get_dish_object(dish_id_in_broken_oven)
                print(f"PBM {time.time()} - Сломавшаяся печь со статусом {dish_object_in_broken_oven.status}")
                new_oven_object = await equipment.ovens.oven_reserve(dish_id_in_broken_oven)
                if broken_oven_object.status == "reserved":
                    broken_oven_object.dish = None
                    await self.change_oven_in_dish(dish_object_in_broken_oven, new_oven_object)
                elif broken_oven_object.status == "occupied":
                    if dish_object_in_broken_oven.status == "cooking":
                        print("Запутить смену лопаток в высокий приоритет")
                        # await self.high_priority_queue.put((BaseRecipy.switch_vane_cut_oven, (new_oven_object.oven_id,
                        #                                                                   broken_oven_id)))
                        # блюдо в печи не стирается пока не выполнится смена
                    elif dish_object_in_broken_oven.status == "baking":
                        print("Запустить ликвидацю блюда")
                        # await self.low_priority_queue.put(dish_object.throwing_away_chain_list)
                elif broken_oven_object.status == "waiting_15" or "waiting_60":
                    # не сделано
                    pass
            broken_oven_object.status = "broken"
            for oven in equipment.ovens.oven_units:
                print(equipment.ovens.oven_units[oven])

        except (BrokenOvenHandlerError, AttributeError):
            pass


class QRCodeHandler(object):
    """
    Это описание
    """
    async def not_found(self, pickup_point):
        print("Заказ не найден")
        await Controllers.set_not_found(pickup_point)

    async def in_progress(self, pickup_point):
        print("Мы еще готовим блюдо")
        await Controllers.set_in_progress(pickup_point)

    async def start_delivery(self, pickup_point):
        pass

    async def time_is_up(self, pickup_point):
        await Controllers.set_time_is_up(pickup_point)

    async def request_delivery_handler(self, order_check_code, pickup_point, current_orders_proceed):
        """Этот метод проверяет, есть ли заказ с таким чек кодом в current_orders_proceed.
        Входные данные params: полученный от контроллера словарь с чек кодом заказа и окном выдачи
        "check_code": int, "pickup": int"""
        print(f"PBM {time.time()} Обрабатываем событе QR_CODE")
        print()

        handlers_options = {1: self.not_found,
                            2: self.in_progress,
                            3: self.start_delivery,
                            4: self.time_is_up
                            }

        OPTIONS = {
            "received": 2,
            "cooking": 2,
            "ready": 3,
            "informed": 3,
            "failed_to_be_cooked": 3
        }

        if order_check_code in current_orders_proceed:
            order_status = current_orders_proceed[order_check_code].status
            try:
                handler_to_launch = handlers_options[OPTIONS[order_status]]

            except KeyError:
                print("статус блюда не распознан")
                handler_to_launch = self.not_found
        else:
            handler_to_launch = self.not_found

        await handler_to_launch(pickup_point)

    async def delivery_request_handler(self, order_check_code):
        """Запускает процедуру выдачи заказа
        ДОБАВИТЬ ОЧИСТКУ поля ПЕЧЬ после упаковке --> oven_unit = None"""
        for dish in self.current_orders_proceed[order_check_code].dishes:
            print("Вот это блюдо выдаем", dish)
            # не сделано


class CookingModeHandlers(BrokenEquipmentHandler, QRCodeHandler):
    """Это описание"""
    pass
