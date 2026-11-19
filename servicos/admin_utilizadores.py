"""Administração de utilizadores: contas novas aparecem primeiro e aprovam-se com um clique."""
from django.contrib import admin, messages
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

User = get_user_model()


def _aprovar(modeladmin, request, queryset, nome_grupo):
    grupo = Group.objects.filter(name=nome_grupo).first()
    if grupo is None:
        modeladmin.message_user(request, f"O grupo {nome_grupo} não existe.", messages.ERROR)
        return
    n = 0
    for utilizador in queryset:
        utilizador.is_active = True
        utilizador.save(update_fields=["is_active"])
        utilizador.groups.add(grupo)
        n += 1
    modeladmin.message_user(
        request, f"{n} conta(s) aprovada(s) como {nome_grupo}.", messages.SUCCESS
    )


class UtilizadorAdmin(UserAdmin):
    list_display = ("email", "username", "is_active", "perfis", "date_joined", "last_login")
    list_filter = ("is_active", "groups", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("is_active", "-date_joined")  # contas por aprovar primeiro
    actions = ["aprovar_tecnico", "aprovar_gestor", "desactivar"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")

    @admin.display(description="Perfis")
    def perfis(self, obj):
        return ", ".join(g.name for g in obj.groups.all()) or "Sem perfil"

    @admin.action(description="Aprovar como Técnico")
    def aprovar_tecnico(self, request, queryset):
        _aprovar(self, request, queryset, "Técnico")

    @admin.action(description="Aprovar como Gestor comercial")
    def aprovar_gestor(self, request, queryset):
        _aprovar(self, request, queryset, "Gestor comercial")

    @admin.action(description="Desactivar contas seleccionadas")
    def desactivar(self, request, queryset):
        n = queryset.exclude(pk=request.user.pk).update(is_active=False)
        self.message_user(request, f"{n} conta(s) desactivada(s).", messages.SUCCESS)


try:
    admin.site.unregister(User)
except NotRegistered:
    pass
admin.site.register(User, UtilizadorAdmin)
