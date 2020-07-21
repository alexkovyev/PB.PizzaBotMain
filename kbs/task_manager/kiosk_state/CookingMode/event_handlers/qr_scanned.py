async def qr_code_handler(self, params):
    """Этот метод проверяет, есть ли заказ с таким чек кодом в current_orders_proceed.
    Входные данные params: полученный от контроллера словарь с чек кодом заказа и окном выдачи
    "ref_id": int, "pickup": int"""
    try:
        order_check_code = params["ref_id"]
        pickup_point = params["pickup"]
    except KeyError:
        print("Ошибка ключа, что делать?")
    set_mode_param = await self.evaluation_status_to_set_mode(order_check_code)
    if set_mode_param == "ready":
        self.orders_requested_for_delivery[order_check_code] = order_check_code
        asyncio.create_task(self.delivery_request_handler(order_check_code))
        self.current_orders_proceed[order_check_code].pickup_point = pickup_point
    await Controllers.set_pickup_point_mode(set_mode_param, pickup_point)
    # не доделано
    # await self.high_priority_queue.put(qr_code_data)


async def evaluation_status_to_set_mode(self, order_check_code):
    """Передает контроллу значение, на основании которого пользователю
    выводится информация о заказе на экране пункта выдачи
    переделать на коды см в ноушн
    если пицца не готова режим ожидания
    """
    CNTRLS_SET_MODE_OPTIONS = {1: "not_found",
                               2: "in_progress",
                               3: "ready"}
    OPTIONS = {
        "received": 2,
        "cooking": 2,
        "ready": 3,
        "informed": 3,
        "failed_to_be_cooked": 3
    }
    if order_check_code in self.current_orders_proceed:
        order_status = self.current_orders_proceed[order_check_code].status
        try:
            set_mode = CNTRLS_SET_MODE_OPTIONS[OPTIONS[order_status]]
        except KeyError:
            print("статус блюда не распознан")
            set_mode = "not_found"
    else:
        set_mode = "not_found"
    return set_mode


async def delivery_request_handler(self, order_check_code):
    """Запускает процедуру выдачи заказа
    ДОБАВИТЬ ОЧИСТКУ поля ПЕЧЬ после упаковке --> oven_unit = None"""
    for dish in self.current_orders_proceed[order_check_code].dishes:
        print("Вот это блюдо выдаем", dish)
        # не сделано