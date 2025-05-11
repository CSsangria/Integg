from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, AccountAppeal

class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        'inactive': _('This account has been banned. Please submit an appeal.'),
    }

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class AccountAppealForm(forms.ModelForm):
    APPEAL_REASONS = [
        ('Mistaken Identity', 'Mistaken Identity - I was not the one who violated the guidelines'),
        ('Accidental Violation', 'Accidental Violation - I violated the guidelines unintentionally'),
        ('No Violation', 'No Violation - I did not violate any guidelines'),
        ('Already Addressed', 'Already Addressed - I have already fixed the issue'),
        ('Content Misunderstood', 'Content Misunderstood - My content was misinterpreted'),
        ('Technical Issue', 'Technical Issue - The violation was due to a technical problem'),
        ('Account Compromised', 'Account Compromised - My account was hacked/compromised'),
        ('Other', 'Other - Not listed above'),
    ]
    
    reason = forms.ChoiceField(choices=APPEAL_REASONS, widget=forms.Select(attrs={'class': 'form-select'}))
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Please provide a detailed explanation of why your account should be reactivated...'
        }),
        required=True
    )
    
    class Meta:
        model = AccountAppeal
        fields = ['reason', 'description'] 