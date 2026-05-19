from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from orders.models import OrderItem
from adminpanel.models import Products
from .models import Review, ReviewImage
from django.db.models import Avg

REVIEWS_PER_PAGE = 6


@login_required
def add_review(request, item_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if item.status != 'DELIVERED':
        return JsonResponse({'error': 'Only delivered items can be reviewed'}, status=400)

    if Review.objects.filter(order_item=item).exists():
        return JsonResponse({'error': 'You have already reviewed this item'}, status=400)

    rating = request.POST.get('rating', '0')
    comment = request.POST.get('comment', '').strip()

    try:
        rating = int(rating)
        if not (1 <= rating <= 5):
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid rating'}, status=400)

    if not comment:
        return JsonResponse({'error': 'Comment is required'}, status=400)

    review = Review.objects.create(
        user=request.user,
        product=item.variant.product,
        order_item=item,
        rating=rating,
        comment=comment,
        is_verified_purchase=True,
    )

    images_urls = []
    for img_file in request.FILES.getlist('images')[:5]:
        ri = ReviewImage.objects.create(review=review, image=img_file)
        images_urls.append(request.build_absolute_uri(ri.image.url))

    product = review.product
    agg = product.reviews.aggregate(avg=Avg('rating'))
    total = product.reviews.count()

    return JsonResponse({
        'success': True,
        'review': {
            'username': request.user.get_full_name() or request.user.username,
            'rating': rating,
            'comment': comment,
            'images': images_urls,
        },
        'avg_rating': round(agg['avg'] or 0, 1),
        'total_reviews': total,
    })


def load_more_reviews(request, slug):
    product = get_object_or_404(Products, slug=slug, is_deleted=False, is_active=True)
    page_num = int(request.GET.get('page', 2))
    qs = product.reviews.select_related('user').prefetch_related('images')
    paginator = Paginator(qs, REVIEWS_PER_PAGE)
    page_obj = paginator.get_page(page_num)

    reviews_data = []
    for r in page_obj:
        reviews_data.append({
            'username': r.user.get_full_name() or r.user.username,
            'rating': r.rating,
            'comment': r.comment,
            'is_verified': r.is_verified_purchase,
            'date': r.created_at.strftime('%b %-d, %Y'),
            'images': [request.build_absolute_uri(img.image.url) for img in r.images.all()],
        })

    return JsonResponse({
        'reviews': reviews_data,
        'has_next': page_obj.has_next(),
    })