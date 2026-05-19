from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from adminpanel.models import Banner
from django.views.decorators.cache import never_cache

@never_cache
@login_required(login_url='adminpanel:admin-login')
def banner_list(request):
    if not request.user.is_superuser:
        return redirect('adminpanel:admin-login')
        
    banners = Banner.objects.filter(is_deleted=False).order_by('-created_at')
    return render(request, 'adminpanel/banners/banner_list.html', {'banners': banners})

@never_cache
@login_required(login_url='adminpanel:admin-login')
def create_banner(request):
    if not request.user.is_superuser:
        return redirect('adminpanel:admin-login')
        
    if request.method == 'POST':
        title = request.POST.get('title')
        subtitle = request.POST.get('subtitle')
        image = request.FILES.get('image')
        button_text = request.POST.get('button_text')
        button_link = request.POST.get('button_link')
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        
        if not title or not image:
            messages.error(request, "Title and Image are required.")
            return redirect('adminpanel:create_banner')
            
        Banner.objects.create(
            title=title,
            subtitle=subtitle,
            image=image,
            button_text=button_text,
            button_link=button_link,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        messages.success(request, "Banner created successfully.")
        return redirect('adminpanel:banner_list')
        
    return render(request, 'adminpanel/banners/banner_form.html', {'action': 'Create'})

@never_cache
@login_required(login_url='adminpanel:admin-login')
def edit_banner(request, pk):
    if not request.user.is_superuser:
        return redirect('adminpanel:admin-login')
        
    banner = get_object_or_404(Banner, pk=pk)
    
    if request.method == 'POST':
        banner.title = request.POST.get('title')
        banner.subtitle = request.POST.get('subtitle')
        banner.button_text = request.POST.get('button_text')
        banner.button_link = request.POST.get('button_link')
        
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        banner.start_date = start_date if start_date else None
        banner.end_date = end_date if end_date else None
        
        if request.FILES.get('image'):
            banner.image = request.FILES.get('image')
            
        banner.save()
        messages.success(request, "Banner updated successfully.")
        return redirect('adminpanel:banner_list')
        
    # Format dates for input fields
    start_date = banner.start_date.strftime('%Y-%m-%d') if banner.start_date else ''
    end_date = banner.end_date.strftime('%Y-%m-%d') if banner.end_date else ''
        
    return render(request, 'adminpanel/banners/banner_form.html', {
        'action': 'Edit',
        'banner': banner,
        'start_date': start_date,
        'end_date': end_date
    })

@never_cache
@login_required(login_url='adminpanel:admin-login')
def delete_banner(request, pk):
    if not request.user.is_superuser:
        from django.http import JsonResponse
        return JsonResponse({'success': False, 'message': 'Unauthorized'})
        
    if request.method == 'POST':
        banner = get_object_or_404(Banner, pk=pk)
        banner.is_deleted = True
        banner.save()
        from django.http import JsonResponse
        return JsonResponse({'success': True, 'message': 'Banner deleted successfully.'})
    from django.http import JsonResponse
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@never_cache
@login_required(login_url='adminpanel:admin-login')
def toggle_banner(request, pk):
    if not request.user.is_superuser:
        from django.http import JsonResponse
        return JsonResponse({'success': False, 'message': 'Unauthorized'})
        
    if request.method == 'POST':
        banner = get_object_or_404(Banner, pk=pk)
        banner.is_active = not banner.is_active
        banner.save()
        status = "activated" if banner.is_active else "deactivated"
        from django.http import JsonResponse
        return JsonResponse({'success': True, 'message': f"Banner {status} successfully.", 'is_active': banner.is_active})
    from django.http import JsonResponse
    return JsonResponse({'success': False, 'message': 'Invalid request'})
