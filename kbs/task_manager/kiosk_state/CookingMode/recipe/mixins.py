import asyncio
import time

# from .utils import DurationEvaluation


class ConfigMixin(object):
    """Временное хранение идентификаторов оборудования"""
    SLICING = "станция нарезки"
    CAPTURE_STATION = "место захватов"
    PRODUCT_CAPTURE_ID = "захват для продуктов"
    PACKING = "станция упаковки"
    GIVE_OUT = "пункт выдачи"
    GARBAGE_STATION = "пункт утилизации"
    STOP_STATUS = "failed_to_be_cooked"


class ToolsMixin(ConfigMixin):

    @staticmethod
    async def is_need_to_change_gripper(current_gripper: str, required_gripper: str):
        """метод проверяет нужно ли менять захват ra_api
        """
        return True if str(current_gripper) != required_gripper else False

    @staticmethod
    async def is_need_to_dance(limit, time_limit):
        """

        :param limit:
        :param time_limit:
        :return:
        """
        if limit is not None and time_limit is not None:
            time_to_dance = time_limit - time.time()
            return time_to_dance if time_to_dance >1 else False
        else:
            return False

    @staticmethod
    async def unpack_filling_data(filling_data):
        """Этот метод распаковывает данные об ингредиенте
        начинки, необходимой для запуска чейна
        """
        filling_item = filling_data["id"]
        cutting_program = filling_data["cut_program"]
        storage_address = filling_data["location"]
        is_last_item = filling_data["is_last"]

        return filling_item, cutting_program, storage_address, is_last_item
