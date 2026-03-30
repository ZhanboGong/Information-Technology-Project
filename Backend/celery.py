import os
from celery import Celery

# 先设置环境变量，再让 Django 初始化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Backend.settings')

app = Celery('Backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 在这里打补丁，或者根本不在这个文件打