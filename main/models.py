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
    name = models.CharField(max_length=100, null=False)
    email = models.EmailField(max_length=254, null=False)
    message = models.TextField(null=False)
    is_read = models.BooleanField(null=False, default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ContactMessage'
        indexes = [
            models.Index(fields=['created_at'], name='idx_contact_created_at'),
        ]

    def __str__(self):
        return self.name