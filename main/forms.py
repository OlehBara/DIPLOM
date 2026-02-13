from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Електронна пошта", required=True)

    class Meta:
        model = User
        fields = ("username", "email")


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="Електронна пошта", required=True)

    class Meta:
        model = User
        fields = ['username', 'email']


from .models import Profile

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']
