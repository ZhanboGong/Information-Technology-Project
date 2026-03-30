import os
import uuid
import shutil
import pandas as pd
import traceback
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action

# 导入你的模型和序列化器
from .models import User, Course, Assignment, Submission, AIEvaluation, KnowledgePoint
from .serializers import (
    AssignmentSerializer,
    SubmissionSerializer,
    MyTokenObtainPairSerializer,
    CourseSerializer
)
from .utils.ai_scorer import AIScorer
from .utils.project_analyzer import ProjectAnalyzer


# --- 1. 身份认证与权限 ---

class MyTokenObtainPairView(TokenObtainPairView):
    """自定义登录视图"""
    serializer_class = MyTokenObtainPairSerializer


class IsTeacher(permissions.BasePermission):
    """教师权限校验"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'teacher'


# --- 2. 教师端视图 ---

class TeacherAssignmentViewSet(viewsets.ModelViewSet):
    """教师管理作业"""
    queryset = Assignment.objects.all().order_by('-id')
    serializer_class = AssignmentSerializer
    permission_classes = [IsTeacher]

    def perform_create(self, serializer):
        kp_ids = self.request.data.get('knowledge_points', [])
        assignment = serializer.save(teacher=self.request.user)
        if kp_ids:
            assignment.knowledge_points.set(kp_ids)

    @action(detail=True, methods=['post'], url_path='publish-all')
    def publish_all_results(self, request, pk=None):
        assignment = self.get_object()
        evals = AIEvaluation.objects.filter(submission__assignment=assignment)
        count = evals.update(is_published=True)
        return Response({"message": f"成功发布 {count} 条成绩记录"})

    @action(detail=False, methods=['post'], url_path='update-score')
    def update_score(self, request):
        submission_id = request.data.get('submission_id')
        new_score = request.data.get('score')
        new_feedback = request.data.get('feedback')
        try:
            evaluation = AIEvaluation.objects.get(submission_id=submission_id)
            evaluation.total_score = new_score
            evaluation.feedback = new_feedback
            evaluation.teacher_reviewed = True
            evaluation.is_published = True
            evaluation.save()
            sub = evaluation.submission
            sub.final_score = new_score
            sub.save()
            return Response({"message": "成绩已更新并发布"})
        except AIEvaluation.DoesNotExist:
            return Response({"error": "评价记录不存在"}, status=404)


class TeacherCourseViewSet(viewsets.ModelViewSet):
    """教师管理课程"""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        return Course.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class TeacherStudentManagementViewSet(viewsets.ViewSet):
    """教师管理学生：批量创建账号"""
    permission_classes = [IsTeacher]

    @action(detail=False, methods=['post'], url_path='import-students')
    def import_students(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "请上传 Excel 或 CSV 文件"}, status=400)
        try:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            df.columns = [c.strip().lower() for c in df.columns]
            created_count = 0
            with transaction.atomic():
                for _, row in df.iterrows():
                    sid = str(row.get('student_id', '')).strip()
                    if not sid or sid == 'nan': continue
                    user, created = User.objects.get_or_create(
                        student_id_num=sid,
                        defaults={
                            'username': sid,
                            'first_name': str(row.get('name', '')).strip(),
                            'class_name': str(row.get('class', '')).strip(),
                            'role': 'student',
                            'password': make_password(sid)
                        }
                    )
                    if created: created_count += 1
            return Response({"message": f"导入成功：新创建了 {created_count} 名学生。"})
        except Exception as e:
            return Response({"error": f"表格解析失败: {str(e)}"}, status=400)


# --- 3. 学生端视图 ---

class StudentAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """学生查看作业"""
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Assignment.objects.filter(course__students=self.request.user).distinct().order_by('-deadline')

    @action(detail=True, methods=['get'], url_path='my-status')
    def my_status(self, request, pk=None):
        assignment = self.get_object()
        submission = Submission.objects.filter(student=request.user, assignment=assignment).order_by(
            '-created_at').first()
        if not submission:
            return Response({"status": "unsubmitted", "message": "尚未提交"})
        evaluation = AIEvaluation.objects.filter(submission=submission, is_published=True).first()
        return Response({
            "status": submission.status,
            "final_score": float(evaluation.total_score) if evaluation else "待公布",
            "feedback": evaluation.feedback if evaluation else "评分处理中",
            "submitted_at": submission.created_at,
            "attempt_count": Submission.objects.filter(student=request.user, assignment=assignment).count()
        })


class StudentCourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)


class StudentSubmissionViewSet(viewsets.ModelViewSet):
    """学生提交接口 (核心加固版)"""
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Submission.objects.filter(student=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        assignment_id = request.data.get('assignment')
        file_obj = request.data.get('file')

        try:
            assignment = Assignment.objects.get(id=assignment_id)
            student = request.user

            # 1. 权限与次数校验
            if not assignment.course.students.filter(id=student.id).exists():
                return Response({"error": "无权提交此作业"}, status=403)

            existing_count = Submission.objects.filter(student=student, assignment=assignment).count()
            if existing_count >= assignment.max_attempts:
                return Response({"error": "提交次数已达上限"}, status=400)

            # 2. 后端独立判断文件类型
            is_zip = file_obj.name.lower().endswith('.zip')
            calculated_sub_type = 'archive' if is_zip else 'file'

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 3. 保存记录
            submission = serializer.save(
                student=student,
                attempt_number=existing_count + 1,
                sub_type=calculated_sub_type,
                status='pending'
            )

            # 4. 进入 Pipeline 编排
            self.run_agent_pipeline(submission)
            return Response({"message": "提交成功，系统处理中..."}, status=201)

        except Exception as e:
            print(f"❌ ViewSet Create Error: {str(e)}")
            return Response({"error": str(e)}, status=500)

    def run_agent_pipeline(self, submission):
        """异步 Agent 编排逻辑 (带深度调试打印)"""
        from .tasks import run_grading_task

        # 确保基础临时目录存在
        temp_base = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_base, exist_ok=True)

        temp_workspace = os.path.join(temp_base, str(uuid.uuid4()))
        os.makedirs(temp_workspace, exist_ok=True)
        entry_point = None

        try:
            print(f"🚀 [Pipeline] 开始处理 Submission: {submission.id}")

            if submission.sub_type == 'archive':
                # 检查物理路径
                file_path = submission.file.path
                print(f"🚀 [Pipeline] 正在检查文件路径: {file_path}")
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"文件未正确保存到磁盘: {file_path}")

                scorer = AIScorer()
                analyzer = ProjectAnalyzer(ai_client=scorer)

                print(f"🚀 [Pipeline] 正在解压至: {temp_workspace}")
                analyzer.unzip_project(file_path, temp_workspace)

                print(f"🚀 [Pipeline] 正在分析项目结构...")
                contexts = scorer.get_rag_contexts(submission)
                task_requirement = contexts.get('l3', "判断主程序入口。")
                entry_point = analyzer.get_entry_point(temp_workspace, task_context=task_requirement)

            # 派发异步任务
            print(f"🚀 [Pipeline] 派发异步任务到 Celery... EntryPoint: {entry_point}")
            run_grading_task.delay(
                submission_id=submission.id,
                temp_workspace=temp_workspace,
                entry_point=entry_point
            )

            submission.status = 'running'
            submission.save()
            print(f"✅ [Pipeline] 状态更新成功：Running")

        except Exception as e:
            print(f"❌ [Pipeline ERROR] Submission {submission.id} 失败:")
            traceback.print_exc()  # 这行是抓贼的关键，会在控制台打印具体哪行错了
            submission.status = 'failed'
            submission.save()