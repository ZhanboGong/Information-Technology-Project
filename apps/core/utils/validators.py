# apps/core/utils/validators.py
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityValidator:
    """
    Custom password complexity validators.
    Following security best practices, mandatory passwords must meet four dimensions of complexity:
    1. Include uppercase letters (A-Z)
    2. Include lowercase letters (a-z)
    3. Include numbers (0-9)
    4. include special characters (like! @#$%^&* etc.)

    This class needs to be used with Django's 'AUTH_PASSWORD_VALIDATORS' option.
    """
    def validate(self, password, user=None):
        """
        Core validation logic: Use regular expressions to sequentially scan the password string.
        """
        # At least one capital letter
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("The password must contain at least one capital letter."),
                code='password_no_upper',
            )
        # At least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("The password must contain at least one lowercase letter."),
                code='password_no_lower',
            )
        # At least one number
        if not re.search(r'\d', password):
            raise ValidationError(
                _("The password must contain at least one number."),
                code='password_no_number',
            )
        # At least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _("The password must contain at least one special character (! @#$%^&* etc.)."),
                code='password_no_special',
            )

    def get_help_text(self):
        """
        :return: Returns the helper text displayed below the front-end form
        """
        return _("Your password must contain uppercase and lowercase letters, numbers, and special characters.")
