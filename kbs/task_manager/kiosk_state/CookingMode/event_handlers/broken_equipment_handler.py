async def broken_equipment_handler(self, event_params, equipment):
    """Этот метод обрабатывает поломки оборудования, поступающий на event_listener
    :param event_params: dict вида {unit_type: str, unit_id: uuid}
    """
    print("Обрабатываем уведомление об поломке оборудования", time.time())
    BROKEN_STATUS = "broken"
    unit_type = event_params["unit_type"]
    unit_id = event_params["unit_name"]
    try:
        if unit_type != "ovens":
            print("Меняем данные оборудования")
            getattr(equipment, unit_type)[unit_id] = False
        else:
            print("Меняем данные печи")
            await self.broken_oven_handler(unit_id)
    except KeyError:
        print("Ошибка данных оборудования")