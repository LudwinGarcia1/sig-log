from apps.core.navigation import NAV_ITEMS


def navigation(request):
    return {"nav_items": NAV_ITEMS}
