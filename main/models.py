from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

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
        # ВАЖЛИВО: назва має збігатися з тим, що ми зробили в MySQL (RENAME TABLE)
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
    user_name = models.CharField(max_length=100, null=False)
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
        indexes = [
            models.Index(fields=['rating'], name='idx_review_rating'),
            models.Index(fields=['created_at'], name='idx_review_created_at'),
        ]

    def __str__(self):
        return f"{self.user_name} - {self.rating}"


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

    class Meta:
        managed = True
        db_table = 'main_enrollment'
        unique_together = ('user', 'course')  # один запис на пару

    def __str__(self):
        return f'{self.user.username} → {self.course.title}'


# Signals to create Profile automatically
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()