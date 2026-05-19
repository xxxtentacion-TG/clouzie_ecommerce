import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import CustomUser
from adminpanel.models import Products, Variants
from adminpanel.utils.sales_analytics import (
    calculate_metrics,
    order_count_for_range,
    revenue_orders_qs,
    sales_for_previous_day,
    successful_orders_qs,
)
from orders.models import Order, OrderItem


def _percent_change(current, previous):
    if previous == 0:
        return 100 if current > 0 else 0
    return int(((current - previous) / previous) * 100)


@login_required(login_url="adminpanel:admin-login")
def admin_dashboard(request):
    if not request.user.is_admin_user:
        return redirect('home_main')

    today            = timezone.localdate()
    this_month_start = today.replace(day=1)
    ist              = timezone.get_current_timezone()
    page_number      = request.GET.get("page", 1)

    # ── All-time metrics ──────────────────────────────────────
    all_time_metrics = calculate_metrics(revenue_orders_qs())

    # ── Monthly metrics ───────────────────────────────────────
    monthly_paid    = revenue_orders_qs().filter(placed_at__date__gte=this_month_start)
    monthly_metrics = calculate_metrics(monthly_paid)

    # ── Today metrics ─────────────────────────────────────────
    today_paid    = revenue_orders_qs().filter(placed_at__date=today)
    today_metrics = calculate_metrics(today_paid)
    today_orders  = successful_orders_qs().filter(placed_at__date=today).count()
    today_refunds = today_metrics["refund_amount"]

    # ── Yesterday comparison ──────────────────────────────────
    yesterday         = today - timedelta(days=1)
    yesterday_revenue = sales_for_previous_day(yesterday)
    revenue_change    = _percent_change(today_metrics["net_revenue"], yesterday_revenue)

    # ── This week vs last week order count ────────────────────
    week_start           = today - timedelta(days=today.weekday())
    prev_week_start      = week_start - timedelta(days=7)
    prev_week_end        = week_start - timedelta(days=1)
    current_week_orders  = order_count_for_range(week_start, today)
    previous_week_orders = order_count_for_range(prev_week_start, prev_week_end)
    orders_change        = _percent_change(current_week_orders, previous_week_orders)

    # ── Order status counts ───────────────────────────────────
    pending_orders   = Order.objects.filter(order_status="PENDING").count()
    delivered_orders = Order.objects.filter(order_status="DELIVERED").count()
    cancelled_orders = Order.objects.filter(order_status="CANCELLED").count()

    # ── Platform totals ───────────────────────────────────────
    total_customers = CustomUser.objects.filter(is_admin_user=False, is_staff=False).count()
    total_products  = Products.objects.filter(is_deleted=False).count()

    # ── Low stock variants ────────────────────────────────────
    low_stock_variants = (
        Variants.objects
        .filter(is_deleted=False, is_active=True, stock__lte=5)
        .select_related("product")
        .order_by("stock")[:10]
    )

    # ── Trending product today ────────────────────────────────
    trending_today = (
        OrderItem.objects
        .filter(order__placed_at__date=today, order__payment_status__in=["PAID", "REFUNDED"])
        .exclude(status="CANCELLED")
        .values("product_name")
        .annotate(qty=Sum("quantity"), revenue=Sum("total"))
        .order_by("-qty")
        .first()
    )
    trending_image = None
    if trending_today:
        try:
            from adminpanel.models import Variants as V
            variant = (
                V.objects
                .filter(product__name=trending_today["product_name"], is_deleted=False)
                .prefetch_related("images")
                .first()
            )
            if variant and variant.images.first():
                trending_image = variant.images.first().image.url
        except Exception:
            pass

    # ── Top 5 products this month ─────────────────────────────
    top_products_monthly = (
        OrderItem.objects
        .filter(
            order__placed_at__date__gte=this_month_start,
            order__payment_status__in=["PAID", "REFUNDED"],
        )
        .exclude(status="CANCELLED")
        .values("product_name")
        .annotate(qty=Sum("quantity"), revenue=Sum("total"))
        .order_by("-revenue")[:5]
    )

    # ── Hourly chart for today (0–23) ─────────────────────────
    hourly_rev_qs = (
        today_paid
        .annotate(hour=ExtractHour("placed_at", tzinfo=ist))
        .values("hour")
        .annotate(revenue=Sum("total_amount"))
        .order_by("hour")
    )
    hourly_cnt_qs = (
        successful_orders_qs()
        .filter(placed_at__date=today)
        .annotate(hour=ExtractHour("placed_at", tzinfo=ist))
        .values("hour")
        .annotate(cnt=Count("id"))
        .order_by("hour")
    )
    rev_by_hour = {r["hour"]: float(r["revenue"] or 0) for r in hourly_rev_qs}
    cnt_by_hour = {r["hour"]: r["cnt"] for r in hourly_cnt_qs}

    hourly_labels  = [f"{h:02d}:00" for h in range(24)]
    hourly_revenue = [rev_by_hour.get(h, 0) for h in range(24)]
    hourly_orders  = [cnt_by_hour.get(h, 0) for h in range(24)]

    today_chart = json.dumps({
        "labels":  hourly_labels,
        "revenue": hourly_revenue,
        "orders":  hourly_orders,
    })

    # ── 14-day trend chart ────────────────────────────────────
    chart_start = today - timedelta(days=13)
    daily_qs = (
        revenue_orders_qs().filter(placed_at__date__gte=chart_start)
        .annotate(day=TruncDate("placed_at", tzinfo=ist))
        .values("day")
        .annotate(revenue=Sum("total_amount"), orders=Count("id"))
        .order_by("day")
    )
    rev_by_day = {r["day"]: float(r["revenue"] or 0) for r in daily_qs}
    ord_by_day = {r["day"]: r["orders"]               for r in daily_qs}
    trend_labels  = [(chart_start + timedelta(days=i)).strftime("%d %b") for i in range(14)]
    trend_revenue = [rev_by_day.get(chart_start + timedelta(days=i), 0) for i in range(14)]
    trend_orders  = [ord_by_day.get(chart_start + timedelta(days=i), 0) for i in range(14)]

    daily_chart = json.dumps({
        "labels":  trend_labels,
        "revenue": trend_revenue,
        "orders":  trend_orders,
    })

    # ── Recent orders ─────────────────────────────────────────
    all_orders_qs = Order.objects.select_related("user").order_by("-placed_at")
    paginator     = Paginator(all_orders_qs, 10)
    recent_orders = paginator.get_page(page_number)

    # ── Insight labels ────────────────────────────────────────
    rev_dir = "↑" if revenue_change >= 0 else "↓"
    ord_dir = "↑" if orders_change >= 0 else "↓"
    revenue_insight = f"Revenue {rev_dir} {abs(revenue_change)}% vs yesterday"
    orders_insight  = f"Orders {ord_dir} {abs(orders_change)}% this week"

    context = {
        # All-time
        "net_revenue":         all_time_metrics["net_revenue"],
        "gross_revenue":       all_time_metrics["gross_revenue"],
        "coupon_discount":     all_time_metrics["coupon_discount"],
        "offer_discount":      all_time_metrics["offer_discount"],
        "refund_total":        all_time_metrics["refund_amount"],
        "avg_order_value":     all_time_metrics["avg_order_value"],
        "total_orders":        all_time_metrics["total_orders"],
        "total_customers":     total_customers,
        "total_products":      total_products,
        # Monthly
        "monthly_revenue":     monthly_metrics["net_revenue"],
        "monthly_orders":      monthly_metrics["total_orders"],
        # Today
        "daily_revenue":       today_metrics["net_revenue"],
        "daily_orders":        today_orders,
        "daily_refunds":       today_refunds,
        "daily_avg":           today_metrics["avg_order_value"],
        # Insights
        "revenue_insight":     revenue_insight,
        "orders_insight":      orders_insight,
        "revenue_change":      revenue_change,
        "orders_change":       orders_change,
        # Status
        "pending_orders":      pending_orders,
        "delivered_orders":    delivered_orders,
        "cancelled_orders":    cancelled_orders,
        # Sections
        "low_stock_variants":  low_stock_variants,
        "trending_today":      trending_today,
        "trending_image":      trending_image,
        "top_products_monthly": top_products_monthly,
        "recent_orders":       recent_orders,
        # Charts
        "today_chart_json":    today_chart,
        "daily_chart_json":    daily_chart,
    }

    return render(request, 'adminpanel/dashboard.html', context)
