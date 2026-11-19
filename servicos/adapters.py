from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


class ContaAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return True

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.is_active = False  # fica a aguardar a aprovação de um administrador
        if commit:
            user.save()
        return user


class SocialAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return False

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return
        User = get_user_model()
        for email in sociallogin.email_addresses:
            if not email.verified:
                continue
            user = User.objects.filter(email__iexact=email.email, is_active=True).first()
            if user:
                sociallogin.connect(request, user)
                return
        messages.error(
            request,
            "Esta conta Google não tem acesso. Peça ao administrador para o registar.",
        )
        raise ImmediateHttpResponse(redirect("account_login"))
