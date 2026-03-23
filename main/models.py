from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class Course(models.Model):
    title = models.CharField(max_length=200, null=False)
    description = models.TextField(null=False)
    category = models.CharField(
        max_length=50,
        choices=[
            ('budgeting', 'Budgeting'),
            ('investing', 'Investing'),
            ('credit', 'Credit'),
            ('pension', 'Pension'),
            ('general', 'General')
        ],
        default='general'
    )
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=False, default=0.0)
    is_active = models.BooleanField(null=False, default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = False
        db_table = 'main_course' 
        indexes = [
            models.Index(fields=['category'], name='idx_course_category'),
            models.Index(fields=['created_at'], name='idx_course_created_at'),
        ]

    def __str__(self):
        return self.title


class CartItem(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    # db_constraint=False дозволяє ігнорувати жорсткі помилки MySQL при розбіжності типів
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_constraint=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True # Django сам створить цю таблицю
        db_table = 'main_cartitem'
        indexes = [
            models.Index(fields=['session_key'], name='idx_cart_session'),
            models.Index(fields=['user'], name='idx_cart_user'),
        ]

    def __str__(self):
        return f"Cart: {self.course.title if self.course else 'Unknown'}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    text = models.TextField(null=False)
    rating = models.PositiveSmallIntegerField(
        null=False,
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    is_approved = models.BooleanField(null=False, default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'Review'
        unique_together = ('user', 'course')
        indexes = [
            models.Index(fields=['course'], name='idx_review_course'),
            models.Index(fields=['user'], name='idx_review_user'),
            models.Index(fields=['rating'], name='idx_review_rating'),
            models.Index(fields=['created_at'], name='idx_review_created_at'),
        ]

    def __str__(self):
        return f"{self.display_name} - {self.rating}"

    @property
    def display_name(self):
        full_name = (self.user.get_full_name() or '').strip()
        return full_name or self.user.username

    @property
    def initials(self):
        name = (self.display_name or '').strip()
        if not name:
            return '??'
        parts = [p for p in name.split() if p]
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return parts[0][:2].upper()


class ContactMessage(models.Model):
    sender = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contact_messages'
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    subject = models.CharField(max_length=200, blank=True, default='')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'main_contactmessage'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} — {self.subject or 'без теми'}"


class Profile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')

    def __str__(self):
        return f'{self.user.username} Profile'


class Enrollment(models.Model):
    """Зберігає придбані курси користувача"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'main_enrollment'
        unique_together = ('user', 'course')  # один запис на пару

    def __str__(self):
        return f'{self.user.username} → {self.course.title}'


class LessonProgress(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson_key = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'main_lessonprogress'
        unique_together = ('user', 'course', 'lesson_key')

    def __str__(self):
        return f'{self.user.username} -> {self.course.title} [{self.lesson_key}]'


class ChatMessage(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    chat_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_chat_messages',
    )
    message = models.TextField()
    is_admin_reply = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'main_chatmessage'
        ordering = ['timestamp']

    def __str__(self):
        return f'{self.sender} → {self.chat_user}: {self.message[:30]}'


# Signals to create Profile automatically
from django.db.models.signals import post_save
from django.contrib.auth.models import User as AuthUser
from django.dispatch import receiver


@receiver(post_save, sender=AuthUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=AuthUser)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()
