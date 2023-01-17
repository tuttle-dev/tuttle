import pandas as pd
from typing import Type


class SingletonDataFrame:
    """
    A singleton class that holds a DataFrame as attribute.
    """

    __instance = None

    @staticmethod
    def getInstance():
        """
        Static access method that returns the same instance of the class everytime it is called.
        """
        if SingletonDataFrame.__instance == None:
            SingletonDataFrame()
        return SingletonDataFrame.__instance

    def __init__(self) -> None:
        """
        Virtually private constructor that ensures only one instance of the class is created.
        """
        if SingletonDataFrame.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            SingletonDataFrame.__instance = self
            self.data = pd.DataFrame()

    @property
    def data(self) -> pd.DataFrame:
        """
        Getter method for the data attribute.
        """
        return self._data

    @data.setter
    def data(self, data: pd.DataFrame) -> None:
        """
        Setter method for the data attribute.
        """
        self._data = data
