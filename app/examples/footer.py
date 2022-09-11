import flet
from flet import Column, Container, Page, Row, Text


def main(page: Page):

    main_content = Column()

    # for i in range(100):
    #     main_content.controls.append(Text(f"Line {i}"))

    page.padding = 0
    page.spacing = 0
    page.horizontal_alignment = "stretch"
    page.add(
        Container(main_content, padding=10, expand=True),
        Row([Container(Text("Footer"), bgcolor="yellow", padding=5, expand=True)]),
    )


flet.app(target=main)
