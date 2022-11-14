import flet
from flet import ( 
    Text, Column,
)
from res import  fonts, colors, spacing

def getHeadlineTxt(txt, size = fonts.headline1Size, color = colors.PRIMARY_COLOR):
    return Text(txt,
                      font_family= fonts.HEADLINE_FONT,
                      color= color,
                      weight=fonts.boldFont,
                      size=size 
                    )

def getHeadlineWithSubtitle(title, subtitle,):
    return  Column(
                    spacing=0,
                    controls=[
                        Text(title, font_family= fonts.HEADLINE_FONT, color=colors.GRAY_DARK_COLOR, size=fonts.body1Size),
                        Text(subtitle, font_family= fonts.HEADLINE_FONT, color=colors.GRAY_COLOR, size=fonts.body2Size),
                    ]
                  )