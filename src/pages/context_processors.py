from .models import SiteSettings, UtilityBarItem


def site_globals(request):
    site_settings = SiteSettings.load()
    utility_bar_items = UtilityBarItem.objects.filter(is_active=True)

    cart_count = 0
    try:
        from src.orders.utils import get_or_create_cart

        cart = get_or_create_cart(request)
        cart_count = cart.get_item_count()
    except Exception:
        pass

    nav_categories = []
    try:
        from src.catalog.models import Category

        nav_categories = Category.objects.filter(parent__isnull=True).order_by(
            "sort_order", "name"
        )
    except Exception:
        pass

    return {
        "site_settings": site_settings,
        "utility_bar_items": utility_bar_items,
        "cart_count": cart_count,
        "nav_categories": nav_categories,
    }
