from flet import Image, Container
from res import image_paths

def getAppLogo():
    return Container(
                     width= 12,   
                     content = Image(
                        src= image_paths.logoPath,
                        fit="cover",
                        semantics_label="tuttle logo"
                        ))