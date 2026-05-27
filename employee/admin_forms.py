from django.contrib.auth.forms import AdminPasswordChangeForm, AdminUserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class SimplePasswordAdminMixin:
    """Skip AUTH_PASSWORD_VALIDATORS for admin password set/reset only."""

    simple_password_help_text = _(
        "Any non-empty password is allowed when set from the admin panel."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password1", "password2", "new_password1", "new_password2"):
            if name in self.fields:
                self.fields[name].help_text = self.simple_password_help_text

    def validate_password_for_user(self, user, password_field_name="password2"):
        password = self.cleaned_data.get(password_field_name)
        if password is not None and password.strip() == "":
            self.add_error(
                password_field_name,
                ValidationError(_("Password cannot be blank."), code="password_blank"),
            )


class SimpleAdminPasswordChangeForm(SimplePasswordAdminMixin, AdminPasswordChangeForm):
    pass


class SimpleAdminUserCreationForm(SimplePasswordAdminMixin, AdminUserCreationForm):
    pass
