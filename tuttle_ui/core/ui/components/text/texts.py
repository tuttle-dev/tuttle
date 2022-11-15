"""Defines different text for display used throughout the app"""

from flet import ( 
    Text, 
)
from res import  fonts, colors
from core.ui.utils.flet_constants import ALIGN_LEFT, START_ALIGNMENT

def get_error_txt(txt : str, size : int = fonts.body2Size, color  : str = colors.ERROR_COLOR, show : bool = True):
    """Displays text formatted for errors / warnings """
    return Text(txt,
                      color= color,
                      size=size,
                      visible= show
                    )