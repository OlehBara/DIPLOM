from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('courses/', views.courses, name='courses'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # Цей рядок обов'язково!
    path('contact/ajax/', views.contact_ajax, name='contact_ajax'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='main/login.html'), name='login'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    path('course/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    path('course/<int:course_id>/delete/', views.delete_course, name='delete_course'),
    path('add-to-cart/<int:course_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('courses/add/', views.add_course, name='add_course'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/process/', views.process_payment, name='process_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),

    # Course 1: Основи бюджетування
    path('lessons/budgeting/1/', views.lesson_budgeting_1, name='lesson_budgeting_1'),
    path('lessons/budgeting/2/', views.lesson_budgeting_2, name='lesson_budgeting_2'),
    path('lessons/budgeting/3/', views.lesson_budgeting_3, name='lesson_budgeting_3'),
    path('lessons/budgeting/4/', views.lesson_budgeting_4, name='lesson_budgeting_4'),

    # Course 2: Фінансове планування сім'ї
    path('lessons/family/1/', views.lesson_family_1, name='lesson_family_1'),
    path('lessons/family/2/', views.lesson_family_2, name='lesson_family_2'),
    path('lessons/family/3/', views.lesson_family_3, name='lesson_family_3'),
    path('lessons/family/4/', views.lesson_family_4, name='lesson_family_4'),

    # Course 3: Фінансова грамотність для початківців
    path('lessons/literacy/1/', views.lesson_literacy_1, name='lesson_literacy_1'),
    path('lessons/literacy/2/', views.lesson_literacy_2, name='lesson_literacy_2'),
    path('lessons/literacy/3/', views.lesson_literacy_3, name='lesson_literacy_3'),
    path('lessons/literacy/4/', views.lesson_literacy_4, name='lesson_literacy_4'),

    # Free courses
    path('course/<int:course_id>/free/', views.free_lesson, name='free_lesson'),
    path('api/mark-lesson-complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
]
