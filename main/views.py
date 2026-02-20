from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.db import models
import json
from django.contrib.auth import login
# from django.contrib.auth.forms import UserCreationForm # Replaced by custom form
from .forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm
from .models import Course, Review, ContactMessage, CartItem, Enrollment


def register(request):
    """Реєстрація нового користувача"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Реєстрація успішна! Ласкаво просимо.')
            return redirect('index')
        else:
            messages.error(request, 'Помилка реєстрації. Перевірте введені дані.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'main/register.html', {'form': form})


@login_required
def profile_view(request):
    """Особистий кабінет користувача"""
    user_courses = CartItem.objects.filter(user=request.user).select_related('course')

    # Для адміна — список усіх повідомлень із форми зворотного зв'язку
    contact_messages = None
    if request.user.is_staff:
        contact_messages = ContactMessage.objects.all().select_related('sender').order_by('-created_at')

    context = {
        'display_name': request.user.username,
        'display_email': request.user.email,
        'user_courses': user_courses,
        'contact_messages': contact_messages,
    }
    return render(request, 'main/profile.html', context)


@login_required
def edit_profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Ваш акаунт оновлено!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'main/edit_profile.html', context)



def index(request):
    """Головна сторінка"""
    # Отримуємо безкоштовні курси (які відображаються як популярні)
    # Strict definition: price=0 AND is_premium=False
    free_courses = Course.objects.filter(is_active=True, is_premium=False, price=0)[:3]
    
    # Отримуємо преміум курси
    # Strict definition: is_premium=True
    premium_courses = Course.objects.filter(is_active=True, is_premium=True)[:3]
    
    # Отримуємо схвалені відгуки
    testimonials = Review.objects.filter(is_approved=True)[:4]
    
    context = {
        'popular_courses': free_courses,  # Mapping free_courses to expected template variable
        'premium_courses': premium_courses,
        'testimonials': testimonials,
    }
    return render(request, 'main/index.html', context)


def courses(request):
    """Сторінка курсів"""
    # Отримуємо курси за категоріями (строга фільтрація)
    premium_courses = Course.objects.filter(is_active=True, is_premium=True)
    
    # "Звичайні" курси (безкоштовні та платні не-преміум) для загального каталогу
    # Використовуємо is_premium=False, щоб преміум курси не потрапляли сюди
    courses_list = Course.objects.filter(is_active=True, is_premium=False)
    
    # Фільтрація за категорією
    category = request.GET.get('category', 'all')
    if category != 'all':
        courses_list = courses_list.filter(category=category)
    
    # Пошук
    search = request.GET.get('search', '')
    if search:
        courses_list = courses_list.filter(
            models.Q(title__icontains=search) | 
            models.Q(description__icontains=search)
        )
    
    context = {
        'courses': courses_list,
        'premium_courses': premium_courses,
        'current_category': category,
        'search_query': search,
    }
    return render(request, 'main/courses.html', context)


def course_detail(request, course_id):
    """Сторінка детального опису курсу"""
    course = get_object_or_404(Course, id=course_id)

    # Рекомендації: інші курси з тієї ж категорії
    related_courses = Course.objects.filter(
        category=course.category,
        is_active=True
    ).exclude(id=course.id)[:3]

    # Перевірка: чи вже придбав користувач цей курс
    is_enrolled = False
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()

    # Перевірка: чи курс вже є в кошику
    in_cart = False
    if request.user.is_authenticated:
        in_cart = CartItem.objects.filter(user=request.user, course=course).exists()
    else:
        session_key = request.session.session_key
        if session_key:
            in_cart = CartItem.objects.filter(session_key=session_key, course=course).exists()

    context = {
        'course': course,
        'related_courses': related_courses,
        'is_enrolled': is_enrolled,
        'in_cart': in_cart,
    }
    return render(request, 'main/course_detail.html', context)


def about(request):
    """Сторінка 'Про нас'"""
    stats = {
        'total_courses': Course.objects.filter(is_active=True).count(),
        'total_reviews': Review.objects.filter(is_approved=True).count(),
        'satisfaction_rate': 98,
    }

    context = {'stats': stats}

    # Секретна інбокс-секція лише для адміна 'mysite'
    if request.user.is_authenticated and request.user.username == 'mysite':
        context['admin_messages'] = ContactMessage.objects.all().order_by('-created_at')

    return render(request, 'main/about.html', context)


def contact(request):
    """Сторінка контактів"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        if name and email and message:
            # Зберігаємо повідомлення в базу
            ContactMessage.objects.create(
                name=name,
                email=email,
                message=message
            )
            messages.success(request, 'Дякуємо, ваше повідомлення відправлено!')
            return redirect('contact')
        else:
            messages.error(request, 'Будь ласка, заповніть всі поля.')
    
    return render(request, 'main/contact.html')


@csrf_exempt
@require_http_methods(["POST"])
def contact_ajax(request):
    """AJAX обробка контактної форми"""
    try:
        # Try JSON first (fetch with Content-Type: application/json)
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            data = json.loads(request.body)
            name    = data.get('name', '').strip()
            email   = data.get('email', '').strip()
            subject = data.get('subject', '').strip()
            message = data.get('message', '').strip()
        else:
            # Fallback: FormData / urlencoded
            name    = request.POST.get('name', '').strip()
            email   = request.POST.get('email', '').strip()
            subject = request.POST.get('subject', '').strip()
            message = request.POST.get('message', '').strip()

        print(f"[contact_ajax] ct={content_type!r} name={name!r} email={email!r} msg={message!r}")

        if name and email and message:
            ContactMessage.objects.create(
                sender=request.user if request.user.is_authenticated else None,
                name=name,
                email=email,
                subject=subject,
                message=message,
            )
            return JsonResponse({'success': True, 'message': 'Дякуємо, ваше повідомлення відправлено!'})
        else:
            return JsonResponse({'success': False, 'message': 'Будь ласка, заповніть усі поля.'})

    except Exception as e:
        import traceback
        print("contact_ajax error:", traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'Помилка: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def enroll_course(request, course_id):
    """AJAX: записати користувача на курс (постійний стан)"""
    try:
        course = get_object_or_404(Course, id=course_id)
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course
        )
        return JsonResponse({
            'success': True,
            'already_enrolled': not created,
            'message': f'Ви успішно придбали курс "{course.title}"!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def add_to_cart(request, course_id):
    """Додавання курсу в кошик (AJAX)"""
    try:
        course = Course.objects.get(id=course_id)
        
        if request.user.is_authenticated:
            # Для авторизованих користувачів
            cart_item, created = CartItem.objects.get_or_create(
                user=request.user,
                course=course
            )
            count = CartItem.objects.filter(user=request.user).count()
        else:
            # Для анонімних користувачів (по сесії)
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
                
            cart_item, created = CartItem.objects.get_or_create(
                session_key=session_key,
                course=course
            )
            count = CartItem.objects.filter(session_key=session_key).count()
            
        return JsonResponse({
            'success': True, 
            'message': f'Курс "{course.title}" додано до кошика',
            'cart_count': count
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Курс не знайдено'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def cart_detail(request):
    """Сторінка кошика"""
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).select_related('course')
    else:
        session_key = request.session.session_key
        if not session_key:
            cart_items = []
        else:
            cart_items = CartItem.objects.filter(session_key=session_key).select_related('course')
            
    total_price = sum(item.course.price for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'main/cart.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def remove_from_cart(request, item_id):
    """Видалення курсу з кошика (AJAX)"""
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.filter(id=item_id, user=request.user).first()
        else:
            session_key = request.session.session_key
            if not session_key:
                return JsonResponse({'success': False, 'message': 'Session not found'})
            cart_item = CartItem.objects.filter(id=item_id, session_key=session_key).first()
            
        if cart_item:
            cart_item.delete()
            
            # Recalculate totals
            if request.user.is_authenticated:
                cart_items = CartItem.objects.filter(user=request.user)
            else:
                cart_items = CartItem.objects.filter(session_key=request.session.session_key)
            
            count = cart_items.count()
            total_price = sum(item.course.price for item in cart_items)
            
            return JsonResponse({
                'success': True,
                'message': 'Курс видалено з кошика',
                'cart_count': count,
                'total_price': float(total_price)
            })
        else:
            return JsonResponse({'success': False, 'message': 'Товар не знайдено'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ──────────────────────────────────────────────
#  ADMIN-ONLY VIEWS
# ──────────────────────────────────────────────
from django.contrib.admin.views.decorators import staff_member_required
from .forms import CourseForm


@staff_member_required
def add_course(request):
    """Адмін: додати новий курс"""
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        course = form.save()
        messages.success(request, f'Курс "{course.title}" успішно додано!')
        return redirect('course_detail', course_id=course.id)
    return render(request, 'main/add_course.html', {'form': form, 'action': 'Додати'})


@staff_member_required
def edit_course(request, course_id):
    """Адмін: редагувати курс"""
    course = get_object_or_404(Course, id=course_id)
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Курс "{course.title}" оновлено!')
        return redirect('course_detail', course_id=course.id)
    return render(request, 'main/add_course.html', {'form': form, 'course': course, 'action': 'Редагувати'})


@staff_member_required
def delete_course(request, course_id):
    """Адмін: видалити курс"""
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        title = course.title
        course.delete()
        messages.success(request, f'Курс "{title}" видалено.')
        return redirect('courses')
    return render(request, 'main/delete_course_confirm.html', {'course': course})

