"""국기 그림과, 국기를 붙인 이름."""

import flet as ft

from senso.flags import flag_png
from senso.origin import Country, country_of


def flag_image(country: Country, height: float = 16) -> ft.Control | None:
    png = flag_png(country.code)
    if png is None:
        return None
    return ft.Image(
        src=png,
        height=height,
        width=height * 1.5,
        fit=ft.BoxFit.CONTAIN,
        tooltip=country.name,
    )


def flagged_name(
    name: str,
    origin: str | None,
    *,
    size: float,
    weight: ft.FontWeight | None = None,
    color: str | None = None,
) -> ft.Control:
    """산지(없으면 이름)에서 나라를 찾아 이름 앞에 국기를 붙인다."""
    text = ft.Text(name, size=size, weight=weight, color=color)
    country = country_of(origin, name)
    image = flag_image(country, height=round(size * 0.9)) if country else None
    if image is None:
        return text
    text.expand = True
    return ft.Row(
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[image, text],
    )
