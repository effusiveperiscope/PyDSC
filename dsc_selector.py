import matplotlib.widgets as mwidgets
from abc import ABC, abstractmethod

class Selector:
    def __init__(self, ax, data, props):
        self.selector = mwidgets.RectangleSelector(ax, self.selector_fn,
            props, interactive=True)
        self.ax = ax
        self.selector.set_active(True)

    @abstractmethod
    def selector_fn(self, eclick, erelease):
        pass

class TgSelector(Selector):
    def __init__(self, ax, data, props = {'facecolor':'blue', 'alpha':0.1}):
        super().__init__(ax, data, props)

    def plot():
        #self.ax

    def selector_fn(self, eclick, erelease):
        result = data.tg_detect2(eclick, erelease)
        pass
