import asyncio
import time

from .utils import DurationEvaluation
from kbs.ra_api.RA import RAError


class ConfigMixin(object):
    """Временное хранение идентификаторов оборудования"""
    SLICING = "станция нарезки"
    CAPTURE_STATION = "место захватов"
    PRODUCT_CAPTURE_ID = "захват для продуктов"
    PACKING = "станция упаковки"
    GIVE_OUT = "пункт выдачи"
    GARBAGE_STATION = "пункт утилизации"
    STOP_STATUS = "failed_to_be_cooked"


class ToolsMixin(DurationEvaluation):

    @staticmethod
    async def is_need_to_change_gripper(current_gripper: str, required_gripper: str):
        """метод проверяет нужно ли менять захват ra_api
        """
        return True if str(current_gripper) != required_gripper else False

    async def chain_execute(self, chain_list, equipment):
        """Метод, вызывающий выполнение чейнов из списка
        Чейн - это какая то непрерывная последовательность действий.
        """
        try:
            for chain in chain_list:
                if not self.is_dish_failed:
                    chain, params = chain
                    await chain(params, equipment)
                else:
                    break
        except RAError:
            print("Ошибка века")
            await self.mark_dish_as_failed()

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

    async def prepare_cooking(self):

        lock = asyncio.Lock()
        async with lock:
            await self.mark_dish_as_started()