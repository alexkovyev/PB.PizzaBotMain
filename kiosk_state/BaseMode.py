class BaseMode(object):
    # переделать на фабрику
    def __init__(self):
        self.is_busy = False
        self.time_left = None



    def is_ok_to_del(self):
        return True if not self.is_busy else False