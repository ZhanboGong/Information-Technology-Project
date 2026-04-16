from django.contrib import admin
from .models import AIServiceLog


@admin.register(AIServiceLog)
class AIServiceLogAdmin(admin.ModelAdmin):
    # The fields displayed on the list page
    list_display = ('created_at', 'service_name', 'total_tokens', 'response_time', 'status_code')

    list_filter = ('service_name', 'status_code', 'created_at')

    search_fields = ('endpoint',)

    # Set the field as read-only
    readonly_fields = ('service_name', 'endpoint', 'prompt_tokens', 'completion_tokens',
                       'total_tokens', 'response_time', 'status_code', 'created_at')

    # Prohibit manual addition of log records
    def has_add_permission(self, request):
        return False