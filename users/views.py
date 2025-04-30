from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from .forms import UserRegisterForm, UserProfileUpdateForm, CustomPasswordChangeForm

# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'users/profile.html')

@login_required
def settings(request):
    profile_form = UserProfileUpdateForm(instance=request.user.userprofile)
    password_form = CustomPasswordChangeForm(request.user)
    
    if request.method == 'POST':
        if 'profile_submit' in request.POST:
            profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user.userprofile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile has been updated!')
                return redirect('settings')
        
        elif 'password_submit' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important to keep the user logged in
                messages.success(request, 'Your password was successfully updated!')
                return redirect('settings')
            else:
                messages.error(request, 'Please correct the error below.')
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'profile': request.user.userprofile
    }
    return render(request, 'users/settings.html', context)
