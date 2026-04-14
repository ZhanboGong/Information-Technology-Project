from django.contrib import admin
from .models import AIServiceLog


@admin.register(AIServiceLog)
class AIServiceLogAdmin(admin.ModelAdmin):
    # 列表页显示的字段
    list_display = ('created_at', 'service_name', 'total_tokens', 'response_time', 'status_code')

    # 过滤器（右侧筛选栏）
    list_filter = ('service_name', 'status_code', 'created_at')

    # 搜索框
    search_fields = ('endpoint',)

    # 设置字段为只读（防止在后台手动篡改日志）
    readonly_fields = ('service_name', 'endpoint', 'prompt_tokens', 'completion_tokens',
                       'total_tokens', 'response_time', 'status_code', 'created_at')

    # 禁止手动添加日志记录
    def has_add_permission(self, request):
        return False