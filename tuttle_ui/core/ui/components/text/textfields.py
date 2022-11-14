import flet
from flet import TextField, TextStyle, padding

from res import colors, fonts, spacing


def getStdTxtField(lbl, hint, keyboardType):
    txtFieldPad = padding.symmetric(horizontal=spacing.SPACE_XS)
    txtFieldHintStyle = TextStyle(color=colors.GRAY_COLOR, size=fonts.captionSize)
        
    return TextField(label=lbl, keyboard_type=keyboardType, content_padding=txtFieldPad, hint_text=hint, 
        hint_style= txtFieldHintStyle, border_color=colors.GRAY_COLOR, focused_border_color=colors.PRIMARY_LIGHT_COLOR, focused_border_width=1)