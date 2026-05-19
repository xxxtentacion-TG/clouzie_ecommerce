import json
import re
from groq import Groq
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from adminpanel.models import Products, Variants
from orders.models import Order
from wallet.models import Wallet
from .models import AIChatMessage


client = Groq(api_key=settings.GROQ_API_KEY)


PRODUCT_KEYWORDS = [
    "jeans", "hoodie", "shirt", "tshirt", "t-shirt", "tee", "oversized",
    "black", "white", "blue", "cargo", "denim", "jacket", "pants",
    "trouser", "outfit", "style", "suggest", "recommend", "wear",
]

WALLET_KEYWORDS = ["wallet", "refund", "payment", "balance"]
ORDER_KEYWORDS = ["order", "track", "delivery", "return", "cancel"]
IGNORE_WORDS = ["suggest", "recommend", "show", "find", "under", "below", "style", "outfit", "wear", "for", "the", "and"]


def message_has_any_word(message, words):
    message = message.lower()
    for word in words:
        if word in message:
            return True
    return False


def get_search_words(message):
    words = re.findall(r"[a-zA-Z0-9]+", message.lower())
    clean_words = []

    for word in words:
        if word.isdigit():
            continue

        if len(word) > 2 and word not in IGNORE_WORDS:
            clean_words.append(word)

    return clean_words


def get_budget(message):
    match = re.search(r"(under|below|less than|upto|up to)\s*(rs\.?|inr|₹)?\s*([0-9][0-9,]*)", message.lower())

    if match:
        return match.group(3).replace(",", "")

    return None


def get_first_variant(product, budget=None):
    variants = Variants.objects.filter(
        product=product,
        is_active=True,
        is_deleted=False,
        stock__gt=0,
    ).order_by("price")

    if budget:
        variants = variants.filter(price__lte=budget)

    return variants.first()


def get_product_image(request, variant):
    if not variant:
        return ""

    image = variant.images.first()

    if image and image.image:
        return request.build_absolute_uri(image.image.url)

    return ""


def search_products(request, message):
    search_words = get_search_words(message)
    budget = get_budget(message)

    products = Products.objects.filter(
        is_active=True,
        is_deleted=False,
        category__is_active=True,
        category__is_deleted=False,
    ).select_related("category").prefetch_related("variants__images")

    for word in search_words:
        products = products.filter(
            Q(name__icontains=word) |
            Q(description__icontains=word) |
            Q(category__name__icontains=word) |
            Q(subcategory__name__icontains=word) |
            Q(variants__color__icontains=word)
        )

    product_list = []

    for product in products.distinct()[:8]:
        variant = get_first_variant(product, budget)

        if not variant:
            continue

        product_list.append({
            "name": product.name,
            "price": str(variant.price),
            "category": product.category.name,
            "image": get_product_image(request, variant),
            "url": f"/products/{product.slug}/",
        })

        if len(product_list) == 4:
            break

    return product_list


def make_product_context(products):
    if not products:
        return "No matching products found."

    lines = []

    for product in products:
        lines.append(f"- {product['name']} - Rs.{product['price']} - {product['category']}")

    return "\n".join(lines)


def get_page_context(path):
    path = (path or "").lower()

    if "/orders" in path:
        return "The user is on the orders page."
    if "/wallet" in path:
        return "The user is on the wallet page."
    if "/checkout" in path:
        return "The user is on the checkout page."
    if "/products" in path:
        return "The user is on the shop page."

    return "The user is browsing CLOUZIE."


@login_required
@require_POST
def ai_chat(request):
    user_message = ""

    try:
        data = json.loads(request.body)
        user_message = (data.get("message") or "").strip()
        page_path = data.get("path") or ""

        if not user_message:
            return JsonResponse({
                "success": False,
                "reply": "Ask me what you would like help with.",
                "products": [],
            })

        is_product_question = message_has_any_word(user_message, PRODUCT_KEYWORDS)
        is_wallet_question = message_has_any_word(user_message, WALLET_KEYWORDS)
        is_order_question = message_has_any_word(user_message, ORDER_KEYWORDS)

        products = []

        if is_product_question:
            products = search_products(request, user_message)

        if is_product_question and not products:
            reply = "No matching products found right now.\n\nTry another style or keyword."
            AIChatMessage.objects.create(
                user=request.user,
                user_message=user_message,
                ai_reply=reply,
            )
            return JsonResponse({
                "success": True,
                "reply": reply,
                "products": [],
            })

        prompt = f"""
You are CLOUZIE AI, a premium fashion ecommerce assistant.
Keep replies short, clean, and stylish.
Rules:
- All prices are in Indian Rupees (₹)
- Never use dollars
- Never mention USD

User message:
{user_message}

Page:
{get_page_context(page_path)}
"""

        if is_product_question:
            prompt += f"""

Available Products:
{make_product_context(products)}

Product rules:
- Recommend only the Available Products listed above.
- Do not invent products or brands.
- If a product is not listed, do not mention it.
"""

        if is_wallet_question:
            wallet = Wallet.objects.filter(user=request.user).first()
            wallet_balance = wallet.balance if wallet else 0
            prompt += f"""

Wallet Balance:
Rs.{wallet_balance}
"""

        if is_order_question:

            latest_order = Order.objects.filter(
                user=request.user
            ).order_by("-placed_at").first()

            if latest_order:

                prompt += f"""

        Latest Order Details:

        Order ID: {latest_order.order_id}

        Order Status: {latest_order.order_status}

        Original Amount: ₹{latest_order.subtotal}

        Discount Applied: ₹{latest_order.discount_amount}

        Final Paid Amount: ₹{latest_order.total_amount}

        Payment Method: {latest_order.payment_method}

        Payment Status: {latest_order.payment_status}

        Important:
        - Final Paid Amount is the actual amount paid after discounts.
        - Never use Original Amount as final amount.
        """

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=180,
        )

        reply = response.choices[0].message.content

        AIChatMessage.objects.create(
            user=request.user,
            user_message=user_message,
            ai_reply=reply,
        )

        return JsonResponse({
            "success": True,
            "reply": reply,
            "products": products,
        })

    except Exception as error:
        print(error)

        reply = "CLOUZIE AI is temporarily unavailable. Please try again in a moment."

        if user_message:
            AIChatMessage.objects.create(
                user=request.user,
                user_message=user_message,
                ai_reply=reply,
            )

        return JsonResponse({
            "success": False,
            "reply": reply,
            "products": [],
        })
