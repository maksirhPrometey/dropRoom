from .models import Cart, CartItem


def get_or_create_cart(request) -> Cart:
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, defaults={})
        return cart

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(
        session_key=session_key, user=None, defaults={}
    )
    return cart


def merge_carts(user, session_key: str) -> None:
    try:
        anon_cart = Cart.objects.get(session_key=session_key, user=None)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for anon_item in anon_cart.items.all():
        item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            variant=anon_item.variant,
            defaults={"quantity": anon_item.quantity},
        )
        if not created:
            item.quantity += anon_item.quantity
            item.save()

    anon_cart.delete()
