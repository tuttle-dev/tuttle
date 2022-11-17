"""Defines different headlines used throughout the app"""

from flet import ( 
    Text, Column,
)
from res import  fonts, colors
from core.ui.utils.flet_constants import TXT_ALIGN_LEFT, START_ALIGNMENT

def get_headline_txt(txt : str, size : int = fonts.headline1Size, color  : str = colors.PRIMARY_COLOR):
    """Displays text formatted as a headline"""
    return Text(txt,
                      font_family= fonts.HEADLINE_FONT,
                      color= color,
                      weight=fonts.boldFont,
                      size=size 
                    )

def get_headline_with_subtitle(title : str, subtitle : str , alignmentInContainer : str = START_ALIGNMENT, txtAlignment : str = TXT_ALIGN_LEFT, titleSize : int = fonts.subtitle1Size, subtitleSize : int = fonts.subtitle2Size):
    """Displays text formatted as a headline with a subtitle below it"""
    return  Column(
                    spacing=0,
                    horizontal_alignment=alignmentInContainer,
                    controls=[
                        Text(title, font_family= fonts.HEADLINE_FONT, color=colors.GRAY_DARK_COLOR, size=titleSize, text_align=txtAlignment),
                        Text(subtitle, font_family= fonts.HEADLINE_FONT, color=colors.GRAY_COLOR, size=subtitleSize, text_align=txtAlignment),
                    ]
                  )