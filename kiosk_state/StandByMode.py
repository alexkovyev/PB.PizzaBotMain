from .BaseMode import BaseMode


class StandBy(BaseMode):
    def __init__(self):
        super().__init__()

    # async def broken_equipment_handler(self, event_params, equipment):
    #     BROKEN_STATUS = "broken"
    #     unit_type = event_params["unit_type"]
    #     unit_id = event_params["unit_name"]
    #     print("Это тип оборудования", unit_type)
    #     try:
    #         if unit_type != "ovens":
    #             print("Меняем данные оборудования")
    #             getattr(equipment, unit_type)[unit_id] = False
    #             print(equipment)
    #         else:
    #             print("Меняем данные печи")
    #             equipment.ovens.oven_units[unit_id].status = BROKEN_STATUS
    #     except KeyError:
    #         print("Ошибка данных оборудования")

