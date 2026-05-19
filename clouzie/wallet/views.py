from django.shortcuts import render
from wallet.models import Wallet, WalletTransaction
from django.core.paginator import Paginator
import json, razorpay
from decimal import Decimal
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


# Create your views here.
def wallet_management(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    tx_qs = wallet.transactions.all().order_by('-created_at')

    paginator = Paginator(tx_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'wallet':   wallet,
        'page_obj': page_obj,
        # keep 'transactions' as an alias so any other template reference still works
        'transactions': page_obj,
    }
    return render(request, "wallet/wallet.html", context)


@csrf_exempt
def create_wallet_topup(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)
    amount = data.get("amount")

    if not amount or float(amount) <= 0:
        return JsonResponse({"error": "Invalid amount"}, status=400)

    amount = Decimal(amount)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    razorpay_order = client.order.create({
        "amount": int(amount * 100),  # paisa
        "currency": "INR",
        "payment_capture": "1"
    })

    return JsonResponse({
        "key": settings.RAZORPAY_KEY_ID,
        "amount": razorpay_order["amount"],
        "order_id": razorpay_order["id"]
    })
    


@csrf_exempt
def verify_wallet_payment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)

    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")
    amount = Decimal(data.get("amount"))

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })

        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        wallet.credit(
            amount,
            description="Wallet top-up via Razorpay"
        )

        return JsonResponse({"success": True, "new_balance": float(wallet.balance)})

    except Exception as e:
        return JsonResponse({"error": "Payment verification failed"}, status=400)