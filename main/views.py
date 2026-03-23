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
from .models import Course, Review, ContactMessage, CartItem, Enrollment, LessonProgress
from django.utils import timezone


def register(request):
    """Реєстрація нового користувача"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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
    # Активні курси (ще не завершені)
    user_courses = Enrollment.objects.filter(
        user=request.user, is_completed=False, course__is_premium=True
    ).select_related('course')

    # Пройдені курси (завершені)
    completed_courses = Enrollment.objects.filter(
        user=request.user, is_completed=True
    ).select_related('course')

    context = {
        'display_name': request.user.username,
        'display_email': request.user.email,
        'user_courses': user_courses,
        'completed_courses': completed_courses,
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
    free_courses = Course.objects.filter(is_active=True, is_premium=False, price=0)
    
    # Отримуємо преміум курси
    # Strict definition: is_premium=True
    premium_courses = Course.objects.filter(is_active=True, is_premium=True)[:3]
    
    # Отримуємо схвалені відгуки
    testimonials = Review.objects.filter(is_approved=True).select_related('user')[:4]
    
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

    # IDs курсів що вже придбані — для показу правильного стану кнопок
    enrolled_ids = set()
    if request.user.is_authenticated:
        enrolled_ids = set(
            Enrollment.objects.filter(user=request.user)
            .values_list('course_id', flat=True)
        )

    context = {
        'courses': courses_list,
        'premium_courses': premium_courses,
        'current_category': category,
        'search_query': search,
        'enrolled_ids': enrolled_ids,
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

    # Static modules list (can be replaced by a DB model later)
    modules = [
        {
            'title': 'Модуль 1: Основи фінансової грамотності',
            'lessons': ['Що таке особистий бюджет?', 'Правило 50/30/20', 'Психологія грошей'],
            'duration': '2 год 15 хв',
        },
        {
            'title': 'Модуль 2: Інструменти управління грошима',
            'lessons': ['Банківські вклади та депозити', 'Картки та cashback-стратегії', 'Мобільні застосунки для бюджету'],
            'duration': '1 год 50 хв',
        },
        {
            'title': 'Модуль 3: Інвестиції для початківців',
            'lessons': ['Фондовий ринок: базові поняття', 'ETF та диверсифікація', 'Ризики та їх мінімізація'],
            'duration': '3 год 10 хв',
        },
        {
            'title': 'Модуль 4: Довгострокова стратегія',
            'lessons': ['Пенсійне планування', 'Страхування та захист активів', 'Ваш фінансовий план на 10 років'],
            'duration': '2 год 30 хв',
        },
    ]

    context = {
        'course': course,
        'related_courses': related_courses,
        'is_enrolled': is_enrolled,
        'in_cart': in_cart,
        'is_purchased': is_enrolled,   # semantic alias used in template
        'modules': modules,
        'course_reviews': Review.objects.filter(
            course=course,
            is_approved=True
        ).select_related('user').order_by('-created_at'),
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


@login_required
@require_http_methods(["POST"])
def mark_premium_lesson_complete(request):
    """AJAX: позначити урок преміум-курсу як завершений"""
    try:
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            data = json.loads(request.body)
        else:
            data = request.POST

        course_id = data.get('course_id')
        lesson_key = (data.get('lesson_key') or '').strip()
        is_final = data.get('is_final', False)

        if isinstance(is_final, str):
            is_final = is_final.lower() in ('1', 'true', 'yes')

        if not course_id or not lesson_key:
            return JsonResponse({'success': False, 'message': 'Missing course_id or lesson_key'}, status=400)

        course = get_object_or_404(Course, id=course_id)

        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return JsonResponse({'success': False, 'message': 'Not enrolled'}, status=403)

        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user,
            course=course,
            lesson_key=lesson_key
        )
        progress.status = 'completed'
        progress.completed_at = timezone.now()
        progress.save()

        if is_final:
            Enrollment.objects.filter(user=request.user, course=course).update(
                is_completed=True,
                completion_date=timezone.now()
            )

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def submit_review(request):
    """AJAX: створити/оновити відгук за курсом"""
    try:
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            data = json.loads(request.body)
        else:
            data = request.POST

        course_id = data.get('course_id')
        text = (data.get('text') or '').strip()
        rating_raw = data.get('rating')

        try:
            rating = int(rating_raw)
        except (TypeError, ValueError):
            rating = 0

        if not course_id or not text or not (1 <= rating <= 5):
            return JsonResponse({'success': False, 'message': 'Invalid data'}, status=400)

        course = get_object_or_404(Course, id=course_id)

        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return JsonResponse({'success': False, 'message': 'Not enrolled'}, status=403)

        Review.objects.update_or_create(
            user=request.user,
            course=course,
            defaults={
                'text': text,
                'rating': rating,
                'is_approved': False,
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Дякуємо! Відгук надіслано на модерацію.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def add_to_cart(request, course_id):
    """Додавання курсу в кошик (AJAX)"""
    try:
        course = Course.objects.get(id=course_id)

        # ── Guard: курс вже куплений — не можна додати знову ──
        if request.user.is_authenticated:
            if Enrollment.objects.filter(user=request.user, course=course).exists():
                return JsonResponse({
                    'success': False,
                    'already_enrolled': True,
                    'message': f'Ви вже придбали курс "{course.title}"',
                })

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


# ──────────────────────────────────────────────
#  PAYMENT (FAKE GATEWAY)
# ──────────────────────────────────────────────

@login_required
def checkout(request):
    """Render the fake payment gateway page."""
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).select_related('course')
    else:
        session_key = request.session.session_key
        cart_items = CartItem.objects.filter(session_key=session_key).select_related('course') if session_key else []

    if not cart_items:
        messages.info(request, 'Ваш кошик порожній.')
        return redirect('cart_detail')

    total_price = sum(item.course.price for item in cart_items)
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'main/payment.html', context)


@login_required
@require_http_methods(["POST"])
def process_payment(request):
    """
    Fake payment processing:
    - Enroll user in every course from the cart
    - Clear the cart
    - Redirect to profile with a success message
    """
    cart_items = CartItem.objects.filter(user=request.user).select_related('course')

    enrolled_count = 0
    for item in cart_items:
        Enrollment.objects.get_or_create(user=request.user, course=item.course)
        enrolled_count += 1

    cart_items.delete()

    if enrolled_count:
        messages.success(
            request,
            f'✅ Оплата успішна! Ви отримали доступ до {enrolled_count} курс(ів).'
        )
    else:
        messages.info(request, 'Кошик був порожній — нічого не оплачено.')

    return redirect('profile')


@login_required
def payment_success(request):
    """
    Confirm payment and enroll the user in all cart courses.

    Steps:
    1. Fetch all CartItem records for the current user.
    2. Create an Enrollment for each course (get_or_create avoids duplicates).
    3. Delete all CartItem records — clears the cart.
    4. Redirect to the profile page where enrolled courses are listed.

    After this view runs:
    - The "Купити" button on course_detail will show "Вже куплено"
      because `is_enrolled` is checked via Enrollment.objects.filter(...).exists()
    - The cart badge count drops to 0.
    """
    cart_items = CartItem.objects.filter(user=request.user).select_related('course')

    enrolled_count = 0
    for item in cart_items:
        Enrollment.objects.get_or_create(user=request.user, course=item.course)
        enrolled_count += 1

    # Clear the cart
    cart_items.delete()

    if enrolled_count:
        messages.success(
            request,
            f'🎉 Вітаємо! Ви успішно придбали {enrolled_count} курс(ів). Приємного навчання!'
        )
    else:
        messages.info(request, 'Кошик був порожній.')

    return redirect('profile')


# ─── Course 1: Основи бюджетування ───────────────────────────────────────────
def _get_premium_course_by_keyword(keyword):
    return Course.objects.filter(is_premium=True, title__icontains=keyword).first()


@login_required
def lesson_budgeting_1(request):
    return render(request, 'main/lesson_budgeting_1.html')

@login_required
def lesson_budgeting_2(request):
    return render(request, 'main/lesson_budgeting_2.html')

@login_required
def lesson_budgeting_3(request):
    return render(request, 'main/lesson_budgeting_3.html')

@login_required
def lesson_budgeting_4(request):
    course = _get_premium_course_by_keyword('бюджет')
    existing_review = None
    if course:
        existing_review = Review.objects.filter(user=request.user, course=course).first()
    return render(request, 'main/lesson_budgeting_4.html', {
        'course': course,
        'existing_review': existing_review,
    })


# ─── Course 2: Фінансове планування сім'ї ────────────────────────────────────
@login_required
def lesson_family_1(request):
    return render(request, 'main/lesson_family_1.html')

@login_required
def lesson_family_2(request):
    return render(request, 'main/lesson_family_2.html')

@login_required
def lesson_family_3(request):
    return render(request, 'main/lesson_family_3.html')

@login_required
def lesson_family_4(request):
    course = _get_premium_course_by_keyword('сім')
    existing_review = None
    if course:
        existing_review = Review.objects.filter(user=request.user, course=course).first()
    return render(request, 'main/lesson_family_4.html', {
        'course': course,
        'existing_review': existing_review,
    })


# ─── Course 3: Фінансова грамотність для початківців ─────────────────────────
@login_required
def lesson_literacy_1(request):
    return render(request, 'main/lesson_literacy_1.html')

@login_required
def lesson_literacy_2(request):
    return render(request, 'main/lesson_literacy_2.html')

@login_required
def lesson_literacy_3(request):
    return render(request, 'main/lesson_literacy_3.html')

@login_required
def lesson_literacy_4(request):
    course = _get_premium_course_by_keyword('грамот')
    existing_review = None
    if course:
        existing_review = Review.objects.filter(user=request.user, course=course).first()
    return render(request, 'main/lesson_literacy_4.html', {
        'course': course,
        'existing_review': existing_review,
    })


# ─── Free Courses ─────────────────────────────────────────────────────────────

# Маппінг: частина назви курсу → шаблон
FREE_COURSE_TEMPLATE_MAP = {
    'Фондовий ринок': 'main/lesson_free_stock.html',
    'Іпотека': 'main/lesson_free_mortgage.html',
    'Пенсійне': 'main/lesson_free_pension.html',
    'Фінансові пастки': 'main/lesson_free_scam.html',
    'Інфляція': 'main/lesson_free_inflation.html',
}


@login_required
def free_lesson(request, course_id):
    """Сторінка безкоштовного уроку"""
    course = get_object_or_404(Course, id=course_id, is_premium=False)

    # Автоматично створюємо Enrollment якщо ще немає
    Enrollment.objects.get_or_create(user=request.user, course=course)

    template = None
    for key, tmpl in FREE_COURSE_TEMPLATE_MAP.items():
        if key in course.title:
            template = tmpl
            break

    if not template:
        template = 'main/lesson_free.html'

    return render(request, template, {'course': course})


@login_required
@require_http_methods(["POST"])
def mark_lesson_complete(request):
    """AJAX: позначити безкоштовний курс як завершений"""
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')

        course = get_object_or_404(Course, id=course_id)
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course
        )
        enrollment.is_completed = True
        enrollment.completion_date = timezone.now()
        enrollment.save()

        return JsonResponse({
            'success': True,
            'message': f'Курс "{course.title}" успішно завершено!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

