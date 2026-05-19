import calendar
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import ExtractHour, ExtractMonth, TruncDate, TruncMonth
from django.utils import timezone

from orders.models import Order, OrderItem, ReturnRequest

MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)
ZERO = Decimal("0.00")

BAD_ORDER_STATUSES = ["CANCELLED", "RETURNED"]
BAD_ITEM_STATUSES  = ["CANCELLED", "RETURNED"]


def decimal_sum(value):
    return Decimal(str(value)) if value else ZERO



def paid_orders_qs():
    """Confirmed-paid orders — source of truth for revenue."""
    return Order.objects.select_related("user").filter(payment_status="PAID")


revenue_orders_qs = paid_orders_qs


def successful_orders_qs():
    """All placed orders (PAID or PENDING, not cancelled)."""
    return (
        Order.objects.select_related("user")
        .filter(payment_status__in=["PAID", "PENDING"])
        .exclude(order_status__in=BAD_ORDER_STATUSES)
    )


def active_items_qs(order_qs):
    return (
        OrderItem.objects
        .filter(order__in=order_qs)
        .exclude(status__in=BAD_ITEM_STATUSES)
    )



def current_period_dates(filter_type, start_str="", end_str=""):
    today = timezone.localdate()
    if filter_type == "daily":
        return today, today
    if filter_type == "weekly":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if filter_type == "monthly":
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        return start, today.replace(day=last_day)
    if filter_type == "yearly":
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    if filter_type == "custom" and start_str and end_str:
        try:
            return (
                datetime.strptime(start_str, "%Y-%m-%d").date(),
                datetime.strptime(end_str,   "%Y-%m-%d").date(),
            )
        except ValueError:
            pass
    return None, None


def apply_order_period(qs, filter_type, start_str="", end_str="", field="placed_at"):
    start, end = current_period_dates(filter_type, start_str, end_str)
    if start and end:
        return qs.filter(**{f"{field}__date__gte": start, f"{field}__date__lte": end})
    return qs



def get_refund_total(order_qs=None):
    """
    Refunds from two sources:
    1. ReturnRequest.refund_amount WHERE status='REFUNDED' (item-level)
    2. Order.total_amount WHERE payment_status='REFUNDED' and no ReturnRequest
    """
    rr_qs = ReturnRequest.objects.filter(status="REFUNDED")
    if order_qs is not None:
        rr_qs = rr_qs.filter(order__in=order_qs)
    item_refunds = decimal_sum(rr_qs.aggregate(t=Sum("refund_amount"))["t"])

    orders_with_rr  = ReturnRequest.objects.values("order_id")
    full_refund_qs  = Order.objects.filter(payment_status="REFUNDED").exclude(id__in=orders_with_rr)
    if order_qs is not None:
        full_refund_qs = full_refund_qs.filter(id__in=order_qs.values("id"))
    order_refunds = decimal_sum(full_refund_qs.aggregate(t=Sum("total_amount"))["t"])

    return item_refunds + order_refunds



def calculate_metrics(order_qs):
    """
    CORRECT business logic (uses stored order data only):

      Gross Revenue  = Sum(OrderItem.original_price × quantity)
      Offer Discount = Sum(OrderItem.offer_discount)          [stored field]
      Coupon Discount= Sum(Order.discount_amount)
      Net Revenue    = Sum(Order.total_amount)                [actual paid]
      Refund Amount  = Sum(ReturnRequest) + fully-refunded orders
    """
    paid_qs    = order_qs.filter(payment_status="PAID")
    items      = active_items_qs(paid_qs)

    gross_expr = ExpressionWrapper(F("original_price") * F("quantity"), output_field=MONEY_FIELD)

    gross_revenue   = decimal_sum(items.aggregate(t=Sum(gross_expr))["t"])
    offer_discount  = decimal_sum(items.aggregate(t=Sum("offer_discount"))["t"])  
    coupon_discount = decimal_sum(paid_qs.aggregate(t=Sum("discount_amount"))["t"])
    net_revenue     = decimal_sum(paid_qs.aggregate(t=Sum("total_amount"))["t"]) 
    refund_amount   = get_refund_total(order_qs)

    total_orders    = paid_qs.count()
    total_customers = paid_qs.values("user").distinct().count()
    avg_order_value = round(net_revenue / total_orders, 2) if total_orders else ZERO

    return {
        "total_orders":     total_orders,
        "gross_revenue":    gross_revenue,
        "offer_discount":   offer_discount,
        "coupon_discount":  coupon_discount,
        "refund_amount":    refund_amount,
        "net_revenue":      net_revenue,
        "avg_order_value":  avg_order_value,
        "total_customers":  total_customers,
    }



def filtered_revenue_orders(filter_type, start_str="", end_str=""):
    return apply_order_period(paid_orders_qs(), filter_type, start_str, end_str)


def filtered_successful_orders(filter_type, start_str="", end_str=""):
    return apply_order_period(successful_orders_qs(), filter_type, start_str, end_str)


def calculate_filtered_metrics(filter_type, start_str="", end_str=""):
    base = apply_order_period(Order.objects.select_related("user"), filter_type, start_str, end_str)
    return calculate_metrics(base)


def sales_for_previous_day(day):
    total = (
        Order.objects
        .filter(payment_status="PAID", placed_at__date=day)
        .aggregate(t=Sum("total_amount"))["t"]
    )
    return decimal_sum(total)


def order_count_for_range(start, end):
    return (
        successful_orders_qs()
        .filter(placed_at__date__gte=start, placed_at__date__lte=end)
        .count()
    )



def _rev_map(order_qs, group_field):
    """Sum(total_amount) grouped by group_field — uses stored paid amount."""
    rows = (
        order_qs.filter(payment_status="PAID")
        .annotate(grp=group_field)
        .values("grp")
        .annotate(rev=Sum("total_amount"))
        .order_by("grp")
    )
    return {r["grp"]: float(r["rev"] or 0) for r in rows}


def _cnt_map(order_qs, group_field):
    rows = (
        order_qs
        .annotate(grp=group_field)
        .values("grp")
        .annotate(cnt=Count("id"))
        .order_by("grp")
    )
    return {r["grp"]: r["cnt"] for r in rows}


def _series(labels, keys, data_map, default=0):
    return {"labels": labels, "data": [data_map.get(k, default) for k in keys]}


def build_chart_data():
    """
    Build chart data for Daily / Weekly / Monthly / Yearly views.
    Revenue = Sum(Order.total_amount) — matches actual paid amount.
    """
    today = timezone.localdate()
    ist   = timezone.get_current_timezone()

    all_paid = Order.objects.all()
    all_ok   = successful_orders_qs()

    hour_field  = ExtractHour("placed_at", tzinfo=ist)
    daily_keys  = list(range(24))
    daily_lbls  = [f"{h:02d}:00" for h in daily_keys]
    d_rev = _rev_map(all_paid.filter(placed_at__date=today), hour_field)
    d_cnt = _cnt_map(all_ok.filter(placed_at__date=today),   hour_field)

    w_start     = today - timedelta(days=today.weekday())
    w_end       = w_start + timedelta(days=6)
    date_field  = TruncDate("placed_at", tzinfo=ist)
    weekly_keys = [w_start + timedelta(days=i) for i in range(7)]
    weekly_lbls = [d.strftime("%a %d") for d in weekly_keys]
    w_paid = all_paid.filter(placed_at__date__gte=w_start, placed_at__date__lte=w_end)
    w_ok   = all_ok.filter(placed_at__date__gte=w_start,   placed_at__date__lte=w_end)
    w_rev  = _rev_map(w_paid, date_field)
    w_cnt  = _cnt_map(w_ok,   date_field)


    m_start  = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    m_end    = today.replace(day=last_day)
    m_keys   = [m_start + timedelta(days=i) for i in range(last_day)]
    m_lbls   = [d.strftime("%d %b") for d in m_keys]
    m_paid   = all_paid.filter(placed_at__date__gte=m_start, placed_at__date__lte=m_end)
    m_ok     = all_ok.filter(placed_at__date__gte=m_start,   placed_at__date__lte=m_end)
    m_rev    = _rev_map(m_paid, date_field)
    m_cnt    = _cnt_map(m_ok,   date_field)

   
    month_field  = ExtractMonth("placed_at", tzinfo=ist)  
    yr_start     = today.replace(month=1, day=1)
    yr_end       = today.replace(month=12, day=31)
    yr_keys      = list(range(1, 13))                   
    yr_lbls      = ["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"]
    yr_paid      = all_paid.filter(placed_at__date__gte=yr_start, placed_at__date__lte=yr_end)
    yr_ok        = all_ok.filter(placed_at__date__gte=yr_start,   placed_at__date__lte=yr_end)
    yr_rev       = _rev_map(yr_paid, month_field)
    yr_cnt       = _cnt_map(yr_ok,   month_field)

    return {
        "revenue": {
            "daily":   _series(daily_lbls,  daily_keys,  d_rev, 0.0),
            "weekly":  _series(weekly_lbls, weekly_keys, w_rev, 0.0),
            "monthly": _series(m_lbls,      m_keys,      m_rev, 0.0),
            "yearly":  _series(yr_lbls,     yr_keys,     yr_rev, 0.0),
        },
        "orders": {
            "daily":   _series(daily_lbls,  daily_keys,  d_cnt, 0),
            "weekly":  _series(weekly_lbls, weekly_keys, w_cnt, 0),
            "monthly": _series(m_lbls,      m_keys,      m_cnt, 0),
            "yearly":  _series(yr_lbls,     yr_keys,     yr_cnt, 0),
        },
    }
