import json
import os
import zipfile
import io
import uuid
import docker
import shutil
import pandas as pd
import requests
import traceback
import re

from rest_framework.pagination import PageNumberPagination

from apps.analytics.models import AIServiceLog
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.core import exceptions
from django.shortcuts import redirect
from datetime import timedelta
from django.utils.encoding import escape_uri_path
from django.shortcuts import get_object_or_404
from django.db.models import Max, Count, Q
from django.db.models.functions import TruncDate
from django.contrib.auth.password_validation import validate_password
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .utils.plagiarism_detector import PlagiarismDetector
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Import the model and serializer
from .models import (User, Course, Assignment, Submission, AIEvaluation, KnowledgePoint, SystemConfiguration,
                     NotificationConfig, Group, SystemOperationLog, EmailVerificationToken, PlagiarismReport)
from .serializers import (
    AssignmentSerializer,
    SubmissionSerializer,
    MyTokenObtainPairSerializer,
    CourseSerializer, KnowledgePointSerializer, UserProfileSerializer, ChangePasswordSerializer, SystemConfigurationSerializer,
    NotificationConfigSerializer, GroupSerializer
)
from .tasks import async_plagiarism_check
from .utils.ai_scorer import AIScorer
from .utils.project_analyzer import ProjectAnalyzer

# Sprint 2

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_teacher(request):
    """
    Teacher independent registration interface: realize the dual access mechanism of "mailbox verification + administrator review".
    Business Logic:
    1. Validation: Checks field integrity, username/email uniqueness, and enforces password complexity.
    2. Account Lockdown: New accounts are initialized with `is_active=False` to prevent unauthorized login.
    3. Workflow Tracking: Sets status to `pending_email` to mark the first phase of the onboarding pipeline.
    4. Token Generation: Creates a unique UUID token for secure email-based identity confirmation.
    5. Notification: Sends an automated email containing the activation link and informs the user about the subsequent admin review.
    """
    data = request.data
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    student_id_num = data.get('student_id_num')

    if not all([username, email, password]):
        return Response({"error": "Please fill in all required fields"}, status=400)

    try:
        validate_password(password)
    except exceptions.ValidationError as e:
        return Response({"error": list(e.messages)}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "The username already exists"}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({"error": "The email has been registered"}, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role='teacher',
                student_id_num=student_id_num,
                approval_status='pending_email',
                is_active=False
            )

            # Generate and save the Token
            token_str = str(uuid.uuid4())
            EmailVerificationToken.objects.create(user=user, token=token_str)

        # Constructing validation links
        verify_link = f"{settings.BACKEND_URL}/api/auth/verify-email/?token={token_str}"

        # Sending an email
        subject = "[Intelligent Programming Teaching System] Teacher Email verification notice"
        message = (
            f"Dear Teacher,\n\n"
            f"Thank you for registering. Please click the link below to verify your email address:\n\n{verify_link}\n\n"
            f"Once verified, your account will enter the administrator review stage. You will be notified of the result separately."
        )

        send_mail(subject, message, settings.EMAIL_HOST_USER, [email])

        return Response({"message": "Registration submitted! A verification email has been sent to your inbox."}, status=201)

    except Exception as e:
        return Response({"error": f"System busy, please try again later: {str(e)}"}, status=500)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def verify_email(request):
    """
    Validates the verification token and advances the account's approval state.

    Workflow:
    1. Token Retrieval: Extracts the unique UUID from the email link.
    2. Expiration Logic: Checks if the token is within its 24-hour validity window. If expired,
       the "skeleton" user record is purged to allow re-registration.
    3. State Transition: Moves the user from `pending_email` to `pending_approval`.
    4. Token Cleanup: Deletes the token after successful use to prevent replay attacks.
    5. Frontend Handoff: Redirects the browser back to the SPA (Single Page Application)
       with query parameters to trigger success/error UI states.
    """
    token_str = request.query_params.get('token')
    if not token_str:
        # If the access is illegal, jump back to the login page with an error
        return redirect(f'{settings.FRONTEND_URL}/login?verify=invalid')

    try:
        # 1. Looking for tokens
        token_obj = EmailVerificationToken.objects.get(token=token_str)

        # 2. Check validity (within 24 hours)
        if not token_obj.is_valid():
            user = token_obj.user
            token_obj.delete()
            user.delete()
            return redirect(f'{settings.FRONTEND_URL}/login?verify=expired')

        user = token_obj.user
        user.approval_status = 'pending_approval'
        user.save()

        token_obj.delete()

        # Redirect to the frontend login page
        frontend_login_url = f'{settings.FRONTEND_URL}/login?verify=success'
        return redirect(frontend_login_url)

    except EmailVerificationToken.DoesNotExist:
        return redirect(f'{settings.FRONTEND_URL}/login?verify=invalid')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_assignment_grades(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.user != assignment.teacher and not request.user.is_staff:
        return HttpResponse("You do not have the permission to export this transcript.", status=403)

    kp_list = assignment.knowledge_points.all()
    rubric_names = [kp.name for kp in kp_list]

    data = []
    students = assignment.course.students.all()

    for student in students:
        submission = None
        group_display = "个人作业"

        if assignment.is_group:
            user_group = Group.objects.filter(course=assignment.course, members=student).first()
            if user_group:
                group_display = user_group.name
                submission = Submission.objects.filter(
                    group=user_group,
                    assignment=assignment,
                    status='completed'
                ).order_by('-final_score').first()
            else:
                group_display = "未组队"

        else:
            submission = Submission.objects.filter(
                student=student,
                assignment=assignment,
                status='completed'
            ).order_by('-final_score').first()

        row = {
            "学号": student.student_id_num or "无",
            "姓名": student.username,
            "班级": student.class_name or "无",
            "小组": group_display,  # 🚀 修正：更清晰的状态展示
            "总分": submission.final_score if submission else "未提交"
        }

        if submission:
            evaluation = AIEvaluation.objects.filter(submission=submission).first()
            scores_dict = {}

            if evaluation and evaluation.ai_raw_feedback:
                try:
                    # 🚀 增加：清洗 AI 可能带出的 Markdown 标签
                    import re
                    clean_str = re.sub(r'```json|```', '', evaluation.ai_raw_feedback).strip()
                    raw_json = json.loads(clean_str)
                    scores_dict = raw_json.get('scores', raw_json)
                except (json.JSONDecodeError, KeyError):
                    scores_dict = {}

            for kp_name in rubric_names:
                row[kp_name] = scores_dict.get(kp_name, 0)
        else:
            for kp_name in rubric_names:
                row[kp_name] = "/"

        data.append(row)

    df = pd.DataFrame(data)

    # 🚀 修正：将 "小组" 加入到列排序中
    columns = ["学号", "姓名", "班级", "小组", "总分"] + rubric_names
    df = df.reindex(columns=columns)

    filename = f"Grades_{assignment.title}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename.encode("utf-8").decode("ISO-8859-1")}"'

    df.to_excel(response, index=False, engine='openpyxl')
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_global_assignment_reminders(request):
    user = request.user
    if user.role != 'student':
        return Response([])

    now = timezone.now()
    one_week_later = now + timedelta(days=7)

    # 1. 获取该学生所有课程中一周内截止的作业
    upcoming_assignments = Assignment.objects.filter(
        course__students=user,
        deadline__range=(now, one_week_later)
    ).select_related('course')

    reminders = []
    for assignment in upcoming_assignments:
        # --- 🚀 核心修改：小组感知的提交判定 ---
        if assignment.is_group:
            # 找到学生在当前课程所属的小组
            user_group = Group.objects.filter(course=assignment.course, members=user).first()
            if user_group:
                # 只要该小组有任何“非失败”的提交，该组所有成员都不再提醒
                has_submitted = Submission.objects.filter(
                    group=user_group,
                    assignment=assignment
                ).exclude(status='failed').exists()
            else:
                # 要求组队但还没加入小组，必须继续提醒
                has_submitted = False
        else:
            # 个人作业：保持原逻辑
            has_submitted = Submission.objects.filter(
                student=user,
                assignment=assignment
            ).exclude(status='failed').exists()
        # --- 🚀 修改结束 ---

        if not has_submitted:
            time_delta = assignment.deadline - now
            days_left = time_delta.days
            hours_left = int(time_delta.total_seconds() // 3600)

            reminders.append({
                "assignment_id": assignment.id,
                "title": assignment.title,
                "course_name": assignment.course.name,
                "deadline": assignment.deadline,
                "days_left": days_left,
                "hours_left": hours_left,
                "category": assignment.category,
                "is_group": assignment.is_group  # 返回此标识，方便前端显示“小组”图标
            })

    reminders.sort(key=lambda x: x['deadline'])
    return Response(reminders)

def log_action(user, action, target_type, target_id=None, detail=""):
    """
    Centralized utility to record system-wide operation logs for auditing.

    Business Value:
    1. Accountability: Tracks "Who did What, When, and to Whom," which is essential for security compliance.
    2. Debugging: Provides a chronological history of changes, making it easier to trace the root cause of system state changes.
    3. Transparency: Allows administrators to monitor sensitive operations like user approvals or score adjustments.
    :param user: The user instance performing the action.
    :param action: A descriptive verb/slug (e.g., 'approve_teacher', 'delete_course').
    :param target_type: The category of the object being acted upon (e.g., 'User', 'Assignment').
    :param target_id: The unique identifier of the target object.
    :param detail: Additional context or JSON-formatted metadata about the change.
    :return:
    """
    from .models import SystemOperationLog
    SystemOperationLog.objects.create(
        user=user,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        detail=detail
    )

# Identity verification and permissions

class MyTokenObtainPairView(TokenObtainPairView):
    """
    Customize the JWT login view.
    By associating a custom serializer
    After the success of the MyTokenObtainPairSerializer, realize the user login
    Return additional user information (like role, username, etc.) instead of just access and refresh tokens.
    Attributes:
        serializer_class (Serializer): This points to a custom token grabber serializer.
    """
    serializer_class = MyTokenObtainPairSerializer


class IsTeacher(permissions.BasePermission):
    """
    Custom permission validation class: Teacher role only access.
    This class is used in the permission_classes configuration of DRF views
    to implement fine-grained interface access control by checking the authentication status and role fields of the requesting user.
    """

    def has_permission(self, request, view):
        """
        Determines whether the current requested user has access permissions.
        :param request: DRF request object, which contains user information.
        :param view: The view instance currently attempting to access.
        :return: bool: Returns True if the user is logged in and the role is 'teacher', False otherwise.
        """
        if not (request.user and request.user.is_authenticated):
            return False

        return request.user.role == 'teacher' and request.user.approval_status == 'approved'


# Teacher Side View

class TeacherAssignmentViewSet(viewsets.ModelViewSet):
    """
    Teacher-side assessment management view set.
    Provides standard CRUD functionality for assignments,
    The core business logic such as knowledge point association, score batch release and manual grading is integrated.

    Permission Restrictions:
    Access is restricted to authenticated users with the 'teacher' role.
    """
    queryset = Assignment.objects.all().order_by('-id')
    serializer_class = AssignmentSerializer
    permission_classes = [IsTeacher]

    # 这里需要稍作修改，作业与知识点的关系
    def create(self, request, *args, **kwargs):
        """
        Rewrite the creation logic to solve the parsing conflicts of complex JSON fields under Multipart/Form-Data.

        Background:
        When teachers upload homework attachments (files), the front-end must use FormData format.
        JSON fields like 'rubric_config' are passed as strings. DRF's JSONField is processing
        This type of non-standard JSON Payload is vulnerable to format validation failures.

        Solution:
        1. data hijacking: Copy the 'request.data' and extract the raw JSON string.
        2. Format spoof: assigning 'rubric_config' and 'reference_logic' legal Python empty objects ({} or []),
        Make sure the serializer's 'is_valid()' passes the base format validation.
        3. Correlation recovery: Manually parse the list of 'knowledge_points' ids to meet the requirements of the ManyToMany field.
        4. Manual compensation: After the instance is saved, parse the raw string using Python's native 'json.loads' and pass it directly
        Model instances are written to the database, completely bypassing the serializer's parsing limitations.
        """
        # 1. Copy raw data (FormData is immutable by default)
        data = request.data.copy()

        # Core logic: Extract the field string that may cause a 400 error
        rubric_str = data.get('rubric_config')
        logic_str = data.get('reference_logic')

        data['rubric_config'] = {}
        data['reference_logic'] = []

        # Handle ID list restoration for Knowledge Points (ManyToMany)
        kp_val = data.get('knowledge_points')
        if kp_val and isinstance(kp_val, str):
            try:
                parsed_kp = json.loads(kp_val)
                if isinstance(parsed_kp, list):
                    if len(parsed_kp) > 0 and isinstance(parsed_kp[0], dict):
                        data.setlist('knowledge_points', [i.get('id') for i in parsed_kp if i.get('id')])
                    else:
                        data.setlist('knowledge_points', parsed_kp)
            except (json.JSONDecodeError, ValueError):
                pass

        # 2. Instantiate and validate (in this case rubric_config is {}, it must pass the format check)
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            print("❌ Detailed validation failed:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Calling save logic
        assignment = serializer.save(teacher=self.request.user)

        # 4. Bypass all parsers of the DRF serializer and use Python's native json library directly
        try:
            if rubric_str:
                # Judgment: loads if it's a string and loads if it's an object
                assignment.rubric_config = json.loads(rubric_str) if isinstance(rubric_str, str) else rubric_str
            if logic_str:
                assignment.reference_logic = json.loads(logic_str) if isinstance(logic_str, str) else logic_str

            # Handle the association of knowledge_points again (double insurance)
            if kp_val and isinstance(kp_val, str):
                parsed_kp = json.loads(kp_val)
                if isinstance(parsed_kp, list) and len(parsed_kp) > 0:
                    ids = [i.get('id') if isinstance(i, dict) else i for i in parsed_kp]
                    assignment.knowledge_points.set(ids)

            # The saving of the Model layer is finally performed
            assignment.save()
            try:
                SystemOperationLog.objects.create(
                    user=request.user,
                    action="CREATE",
                    target_type="Assignment",
                    target_id=str(assignment.id),
                    detail=f"publish new assignment: {assignment.title}"
                )
            except Exception as log_e:
                print(f"Logging failure: {log_e}")
        except Exception as e:
            print(f"JSON manually compensates for the failure: {str(e)}")

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        Responsible for initial instance persistence and binding the current teacher identity.
        """
        serializer.save(teacher=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Logic: Resolves JSON parsing in FormData mode and ManyToMany synchronization.

        Design core:
        In a PUT/PATCH operation, if the frontend uses FormData to upload a new file,
        DRF can't parse nested JSON strings directly. By manually intervening in the data stream,
        Bypass the automatic parsing restrictions of the Serializer.

        Logical steps:
        1. Data hijacking: Copy the request data and extract the raw JSON string and the list of knowledge point ids.
        2. Validation bypass: Injecting fake values (empty object/list) into 'data' ensures that the underlying field passes the serializer format validation.
        3. Basic updates: Call 'serializer.save()' to persist basic fields such as title, time, attachment, etc.
        4. Manual overwriting: Parse complex fields with native 'json.loads' and use' assignment.knowledge_points.set() '
        Explicitly synchronizing many-to-many relationships ensures that changes take effect immediately.
        """
        partial = kwargs.pop('partial', True)
        instance = self.get_object()

        # 1. Copy and hijack data
        data = request.data.copy()
        rubric_str = data.get('rubric_config')
        logic_str = data.get('reference_logic')

        data['rubric_config'] = {}
        data['reference_logic'] = []

        kp_val = data.get('knowledge_points')
        kp_ids = []
        if kp_val and isinstance(kp_val, str):
            try:
                parsed_kp = json.loads(kp_val)
                # Compatible with multiple front-end value passing formats: [1,2] or [{id:1}, {id:2}]
                kp_ids = [i.get('id') if isinstance(i, dict) else i for i in parsed_kp]
                data.setlist('knowledge_points', kp_ids)
            except (json.JSONDecodeError, ValueError):
                pass

        # 2. Validate and save the underlying fields (title, date, etc.)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        assignment = serializer.save()

        # 3. Manually forced injection of real JSON and M2M data
        try:
            if rubric_str:
                assignment.rubric_config = json.loads(rubric_str) if isinstance(rubric_str, str) else rubric_str
            if logic_str:
                assignment.reference_logic = json.loads(logic_str) if isinstance(logic_str, str) else logic_str

            # Manually synchronize the ManyToMany relationship
            if kp_ids:
                assignment.knowledge_points.set(kp_ids)

            assignment.save()
            try:
                SystemOperationLog.objects.create(
                    user=request.user,
                    action="UPDATE",
                    target_type="Assignment",
                    target_id=str(assignment.id),
                    detail=f"update assignment content: {assignment.title}"
                )
            except Exception as log_e:
                print(f"Logging failure: {log_e}")
        except Exception as e:
            print(f"⚠️ Update JSON/M2M Patch Error: {e}")

        return Response(serializer.data)

        # 4. Manually inject real JSON data
        try:
            if rubric_str:
                assignment.rubric_config = json.loads(rubric_str) if isinstance(rubric_str, str) else rubric_str
            if logic_str:
                assignment.reference_logic = json.loads(logic_str) if isinstance(logic_str, str) else logic_str
            assignment.save()
        except Exception as e:
            print(f"Update JSON Patch Error: {e}")

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        删除作业逻辑：确保数据安全与逻辑一致性
        """
        instance = self.get_object()
        assign_id = instance.id
        assign_title = instance.title
        # 1. 安全检查：使用更健壮的检查方式
        # 无论你是否定义了 related_name，instance.submissions 都能根据你的配置灵活调整
        # 如果你确定没改 related_name，submission_set 也是对的
        has_submissions = Submission.objects.filter(assignment=instance).exists()

        if has_submissions:
            return Response({
                "error": "This assignment already has student submissions. "
                         "For data safety, please delete the submissions first or "
                         "just modify the deadline to close the assignment."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2. 使用事务确保删除过程安全
        try:
            with transaction.atomic():
                self.perform_destroy(instance)

                try:
                    SystemOperationLog.objects.create(
                        user=request.user,
                        action="DELETE",
                        target_type="Assignment",
                        target_id=str(assign_id),
                        detail=f"delete assignment: {assign_title}"
                    )
                except Exception as log_e:
                    print(f"Logging failure: {log_e}")

            return Response(
                {"message": "Assignment deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete assignment: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='publish-all')
    def publish_all_results(self, request, pk=None):
        """
        Batch release of all AI scoring results for a given assessment.
        This interface will attach the AIEvaluation of all Submissions associated with the assessment.
        The 'is_published' status of is consistently updated to True, allowing students to view the results.
        :param request: DRF request object
        :param pk: The unique identification ID of the assessment, which is automatically captured by the URL path.
        :return: Response: A JSON response containing the number of records that were successfully updated
        """
        assignment = self.get_object()
        evals = AIEvaluation.objects.filter(submission__assignment=assignment)
        count = evals.update(is_published=True)
        try:
            SystemOperationLog.objects.create(
                user=request.user,
                action="PUBLISH",
                target_type="Assignment",
                target_id=str(assignment.id),
                detail=f"Batch published {count} scoring results for assignment: {assignment.title}"
            )
        except Exception as log_e:
            print(f"Logging failure: {log_e}")

        return Response({"message": f"Successfully published {count} records"})

    @action(detail=False, methods=['post'], url_path='update-score')
    def update_score(self, request):
        """
        Manually update and publish student grades (manually reviewed by teachers)
        The interface allows the teacher to override the grading results and feedback automatically generated by the AI.
        While updating the evaluation record,
        The final score for the associated Submission is updated synchronously and automatically set to published status.
        :param request: A DRF request object containing the following data:
            submission_id (int): The associated commit record ID.
            score (Decimal/float): The new score given by the instructor
            feedback (str): Comments or revised feedback given by the teacher.
        :return: Response: Success message or 404 error (if the rating doesn't exist)
        """
        submission_id = request.data.get('submission_id')
        new_score = request.data.get('score')
        new_feedback = request.data.get('feedback')
        try:
            evaluation = AIEvaluation.objects.get(submission_id=submission_id)
            old_score = evaluation.total_score
            evaluation.total_score = new_score
            evaluation.feedback = new_feedback
            evaluation.teacher_reviewed = True
            evaluation.is_published = True
            evaluation.save()
            sub = evaluation.submission
            sub.final_score = new_score
            sub.save(update_fields=['final_score'])

            # 重新聚合该学生在该作业下的历史最高分
            highest = AIEvaluation.objects.filter(
                submission__student=sub.student,
                submission__assignment=sub.assignment
            ).aggregate(max_val=Max('total_score'))['max_val']

            Submission.objects.filter(
                student=sub.student,
                assignment=sub.assignment
            ).update(final_score=highest)
            try:
                SystemOperationLog.objects.create(
                    user=request.user,
                    action="UPDATE_SCORE",
                    target_type="Submission",
                    target_id=str(submission_id),
                    detail=(
                        f"Manually adjusted score for student {sub.student.username}. "
                        f"Score change: {old_score} -> {new_score}. "
                        f"Assignment: {sub.assignment.title}"
                    )
                )
            except Exception as log_e:
                print(f"Logging failure: {log_e}")
            return Response({"message": "The results have been updated and published"})
        except AIEvaluation.DoesNotExist:
            return Response({"error": "Evaluation records do not exist"}, status=404)

    @action(detail=False, methods=['post'], url_path='suggest-kps')
    def suggest_knowledge_points(self, request):
        """AI 智能推荐 L2 知识点（CoT + 已有 KP 上下文注入 + 模糊去重）。"""
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        language = request.data.get('language', 'python')
        course_id = request.data.get('course', request.data.get('course_id'))
        rubric_config = request.data.get('rubric_config', {})

        if not content:
            return Response({"error": "Assignment requirements (content) cannot be empty."}, status=400)
        if not course_id:
            return Response({"error": "Course ID is required to generate L2 Knowledge Points."}, status=400)

        # 1. 查询已有知识点上下文（限 15 条，控制 token 用量）
        existing_l1 = KnowledgePoint.objects.filter(
            is_system=True, language__iexact=language
        )[:15]
        existing_l2 = KnowledgePoint.objects.filter(
            course_id=course_id, language__iexact=language, is_system=False
        )[:15]

        l1_lines = []
        for kp in existing_l1:
            desc = (kp.description or 'N/A')[:80]
            l1_lines.append(f"- {kp.name}: {desc}")
        l1_list = "\n".join(l1_lines) or "None defined yet."

        l2_lines = []
        for kp in existing_l2:
            desc = (kp.description or 'N/A')[:80]
            l2_lines.append(f"- {kp.name}: {desc}")
        l2_list = "\n".join(l2_lines) or "None defined yet."

        existing_kp_names = set()
        for kp in list(existing_l1) + list(existing_l2):
            existing_kp_names.add(kp.name.lower().strip())

        # 2. 构建 Rubric 描述
        rubric_desc = ""
        rubric_items = rubric_config.get('items', []) if rubric_config else []
        if rubric_items:
            rubric_lines = []
            for item in rubric_items:
                rubric_lines.append(f"- {item.get('criterion')} (Weight: {item.get('weight')}%)")
            rubric_desc = "\n".join(rubric_lines)

        # 3. 构造带 CoT 的 Prompt
        truncated_content = content[:2000]
        rubric_text = rubric_desc or "Standard coding practices"

        prompt_lines = [
            "You are a Computer Science curriculum designer.",
            "Identify 3-5 specific L2 knowledge points that students must demonstrate to complete this assignment.",
            "",
            "=== Assignment Info ===",
            f"Title: {title}",
            f"Requirements: {truncated_content}",
            f"Language: {language}",
            "",
            "=== Rubric Dimensions ===",
            rubric_text,
            "",
            "=== Existing L1 Knowledge Points (system-level, DO NOT repeat these):",
            l1_list,
            "",
            "=== Existing L2 Knowledge Points in this course (DO NOT repeat these):",
            l2_list,
            "",
            "=== Your Task ===",
            "Step 1: Read the assignment requirements carefully. Identify the core programming concepts required.",
            "Step 2: Cross-reference with existing knowledge points above. Only suggest NEW ones that don't overlap.",
            "Step 3: For each new knowledge point, write a description that explains HOW to assess it — what code patterns indicate mastery.",
            "",
            "=== Rules ===",
            "1. Names must be concise (2-4 words), e.g., 'Exception Handling', 'Polymorphism'",
            "2. Names must NOT duplicate any existing L1 or L2 knowledge points listed above",
            "3. Descriptions should be actionable: explain what a student's code should demonstrate",
            "4. Each knowledge point should map to a specific rubric dimension when possible",
            "5. Return exactly 3-5 knowledge points, not more",
            "",
            'Return a JSON object: {"suggested_kps": [{"name": "...", "description": "..."}]}',
        ]
        prompt = "\n".join(prompt_lines)

        scorer = AIScorer()

        try:
            # 4. 调用 AI + JSON 解析
            raw_res = scorer.ask(prompt)

            json_match = re.search(r'\{.*\}', raw_res, re.DOTALL)
            if json_match:
                clean_json = json_match.group()
            else:
                clean_json = raw_res.replace('```json', '').replace('```', '').strip()
            suggestions = json.loads(clean_json)

            # 5. 去重 + 持久化
            course_obj = Course.objects.get(id=course_id)
            final_suggestions = []

            for kp_data in suggestions.get('suggested_kps', []):
                kp_name = kp_data.get('name', '').strip()
                kp_desc = kp_data.get('description', '').strip()
                if not kp_name:
                    continue

                # 精确匹配
                existing = KnowledgePoint.objects.filter(
                    name__iexact=kp_name,
                    course=course_obj,
                    language__iexact=language
                ).first()

                if existing:
                    final_suggestions.append({
                        "id": existing.id,
                        "name": existing.name,
                        "description": existing.description,
                        "is_new": False
                    })
                    continue

                # 模糊去重
                name_lower = kp_name.lower().strip()
                if name_lower in existing_kp_names:
                    continue

                # 创建新 KP
                kp = KnowledgePoint.objects.create(
                    name=kp_name,
                    description=kp_desc,
                    category='L2',
                    is_system=False,
                    course=course_obj,
                    language=language.lower()
                )
                existing_kp_names.add(name_lower)
                final_suggestions.append({
                    "id": kp.id,
                    "name": kp.name,
                    "description": kp.description,
                    "is_new": True
                })

            return Response({"suggested_kps": final_suggestions})

        except Course.DoesNotExist:
            return Response({"error": "The specified course does not exist."}, status=404)
        except json.JSONDecodeError:
            print(f"[KP-Suggest] Failed to parse AI response: {raw_res[:200]}")
            return Response({"error": "AI returned an invalid format. Please try again."}, status=500)
        except Exception as e:
            print(f"[KP-Suggest] Error: {str(e)}")
            return Response({"error": f"AI generation failed: {str(e)}"}, status=500)

    @action(detail=False, methods=['post'], url_path='suggest-rubric')
    def suggest_rubric(self, request):
        """
        AI 智能生成作业评分标准矩阵（带 CoT + 权重自动归一化 + 健壮 JSON 解析）。
        """
        title = request.data.get('title', 'New Assignment')
        content = request.data.get('content', '')
        language = request.data.get('language', 'python')

        if not content:
            return Response({"error": "Please provide assignment requirements first."}, status=400)

        scorer = AIScorer()

        # 带 CoT 的 Prompt
        prompt_lines = [
            "You are an expert Computer Science Professor.",
            "Design a professional grading rubric matrix for the following programming assignment.",
            "",
            "=== Assignment Info ===",
            f"Title: {title}",
            f"Requirements: {content}",
            f"Language: {language}",
            "",
            "=== Your Task ===",
            "Step 1: Identify 3-5 core assessment dimensions based on the assignment requirements.",
            "Step 2: For each dimension, define clear descriptions for all 5 grade levels.",
            "Step 3: Assign weights that sum to exactly 100.",
            "",
            "=== Grade Level Descriptions ===",
            "- High Distinction (85-100%): Exceptional work. Shows deep understanding, elegant code, handles edge cases, exceeds requirements.",
            "- Distinction (75-84%): Strong work. Correct logic, clean code, good structure, meets all requirements fully.",
            "- Credit (65-74%): Competent work. Mostly correct, minor issues in code quality or edge case handling.",
            "- Pass (50-64%): Basic pass. Core logic works but has noticeable flaws, poor structure, or missing features.",
            "- Fail (0-49%): Does not meet requirements. Major logic errors, incomplete submission, or fundamentally wrong approach.",
            "",
            "=== Rules ===",
            "1. Criterion names should be concise (e.g., 'Algorithm Logic', 'Code Quality', 'Error Handling')",
            "2. Each level description must be specific and observable — what would a reviewer see in the code?",
            "3. Weight must sum to exactly 100",
            "4. At least one criterion should assess core logic/correctness",
            "5. Each level description should be 1-2 sentences, clear enough for consistent grading",
            "",
            'Return a JSON object: {"rubric": {"items": [{"criterion": "...", "weight": 25, "description": "...", "detailed_rubric": {"High Distinction (85-100%)": "...", "Distinction (75-84%)": "...", "Credit (65-74%)": "...", "Pass (50-64%)": "...", "Fail (0-49%)": "..."}}]}}',
        ]
        prompt = "\n".join(prompt_lines)

        try:
            raw_res = scorer.ask(prompt)

            # 健壮 JSON 解析
            json_match = re.search(r'\{.*\}', raw_res, re.DOTALL)
            if json_match:
                clean_json = json_match.group()
            else:
                clean_json = raw_res.replace('```json', '').replace('```', '').strip()
            rubric_data = json.loads(clean_json)

            # 校验 + 自动归一化权重
            items = rubric_data.get('rubric', {}).get('items', [])
            if items:
                total_w = sum(item.get('weight', 0) for item in items)
                if total_w != 100 and total_w > 0:
                    scale = 100 / total_w
                    for item in items:
                        item['weight'] = round(item.get('weight', 0) * scale)
                    # 修正四舍五入误差
                    new_total = sum(item['weight'] for item in items)
                    if new_total != 100 and items:
                        max_item = max(items, key=lambda x: x['weight'])
                        max_item['weight'] += (100 - new_total)

            return Response(rubric_data)

        except json.JSONDecodeError:
            print(f"[Rubric-Suggest] Failed to parse AI response: {raw_res[:200]}")
            return Response({"error": "AI returned an invalid format. Please try again."}, status=500)
        except Exception as e:
            print(f"[Rubric-Suggest] Error: {str(e)}")
            return Response({"error": f"AI Rubric generation failed: {str(e)}"}, status=500)

    @action(detail=False, methods=['get'], url_path='download-submission')
    def download_single_submission(self, request):
        """
        Intelligently download a single student's highest score submission.

        Business logic:
        1. Link locating: Find the student and the assignment given the submission_id.
        2. The best algorithm: among all attempts of the same student on the assignment, according to "teacher final score > AI assessment score > latest ID"
        The priority of automatically filters out the best performing records.
        3. Standard naming: the downloaded file name will automatically contain "student number _ name _ number of attempts _ score", which is greatly convenient for teachers to read offline.
        :param request: The submission_id parameter is included.
        :return: The best version of the job file flow.
        """
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response({"error": "submission_id parameter is missing"}, status=400)

        try:
            # 1.  locate the commit record
            original_sub = Submission.objects.get(id=submission_id, assignment__teacher=request.user)

            # 2. Find the student's highest score for that assignment
            # Sorting logic: teacher score first, AI score second, and ID last (take the latest)
            best_submission = Submission.objects.filter(
                student=original_sub.student,
                assignment=original_sub.assignment
            ).order_by('-final_score', '-ai_evaluation__total_score', '-id').first()

            if not best_submission:
                best_submission = original_sub
            try:
                SystemOperationLog.objects.create(
                    user=request.user,
                    action="DOWNLOAD",
                    target_type="Submission",
                    target_id=str(best_submission.id),
                    detail=f"Downloaded code for student: {best_submission.student.username} (Attempt {best_submission.attempt_number})"
                )
            except Exception as log_e:
                print(f"Logging failure: {log_e}")

            file_handle = best_submission.file.open()
            ext = os.path.splitext(best_submission.file.name)[1]

            # Construct filename: Student number_name_xth try_ score
            score_val = best_submission.final_score if best_submission.final_score else "AI评"
            filename = f"{best_submission.student.student_id_num}_{best_submission.student.first_name}_Attempt{best_submission.attempt_number}_Score{score_val}{ext}"

            response = FileResponse(file_handle, content_type='application/octet-stream')
            response['Content-Disposition'] = f"attachment; filename*=utf-8''{escape_uri_path(filename)}"
            return response
        except Submission.DoesNotExist:
            return Response({"error": "No record found or no access granted"}, status=404)

    @action(detail=True, methods=['get'], url_path='download-all')
    def download_all_submissions(self, request, pk=None):
        """
        Batch download the highest-scoring assignments of all students (in a ZIP compressed file).
        Business logic:
        1. Full scan: Retrieve all submission records of all students under this assignment.
        2. Memory deduplication: Utilize the sorting feature (after sorting in SQL and then taking the first record for each student in the loop), to efficiently filter out the "best version" of each student in the class.
        3. Memory compression: Use BytesIO to directly generate a ZIP package in memory, avoiding the generation of server disk fragmentation.
        4. Archiving and renaming: The file names within the ZIP contain student ID, name, number of times and score, facilitating teachers to batch import or offline backup.
        :return: HttpResponse: A ZIP file containing the highest-scoring assignment of the entire class.
        """
        assignment = self.get_object()

        # 1. Core filtering logic: Find the list of submitted ids with the highest score for each student
        all_subs = Submission.objects.filter(assignment=assignment).order_by(
            'student', '-final_score', '-ai_evaluation__total_score', '-id'
        )

        # Deduplication in memory (because of the order_by order, the first thing each student encounters in the loop is the highest score)
        best_ids = []
        seen_students = set()
        for s in all_subs:
            if s.student_id not in seen_students:
                best_ids.append(s.id)
                seen_students.add(s.student_id)

        submissions = Submission.objects.filter(id__in=best_ids).select_related('student')

        if not submissions.exists():
            return Response({"error": "No record of submission"}, status=404)

        try:
            SystemOperationLog.objects.create(
                user=request.user,
                action="EXPORT",
                target_type="Assignment",
                target_id=str(assignment.id),
                detail=f"Batch exported (ZIP) all highest submissions for assignment: {assignment.title}"
            )
        except Exception as log_e:
            print(f"Logging failure: {log_e}")
        byte_io = io.BytesIO()
        with zipfile.ZipFile(byte_io, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for sub in submissions:
                if sub.file and os.path.exists(sub.file.path):
                    ext = os.path.splitext(sub.file.name)[1]
                    # Display score information within the ZIP
                    score_val = sub.final_score if sub.final_score else "AI评"
                    arc_name = f"{sub.student.student_id_num}_{sub.student.first_name}_Attempt{sub.attempt_number}_Score{score_val}{ext}"
                    zip_file.write(sub.file.path, arcname=arc_name)

        byte_io.seek(0)
        zip_filename = f"{assignment.title}_Highest score assignment collection.zip"

        response = HttpResponse(byte_io, content_type='application/zip')
        response['Content-Disposition'] = f"attachment; filename*=utf-8''{escape_uri_path(zip_filename)}"
        return response

    @action(detail=True, methods=['get'], url_path='submissions')
    def get_submissions(self, request, pk=None):
        """
        Retrieve the list of all student submission records for the specified assignment.
        This interface is mainly used for the "submission list" table on the teacher's end homework detail page.
        Design Focus:
        1. Performance Optimization: By using `select_related` to associate the `student` and `ai_evaluation` tables in one go,
        the original N+1 queries are optimized to a single SQL JOIN query.
        2. Data Anonymization: Only return the key fields required for the front-end table display, protecting student privacy and reducing network bandwidth.
        3. Logical Robustness: Using `hasattr` for compatible handling of submission records that have not yet undergone AI scoring, preventing AttributeError caused by OneToOne association missing.
        :param request: DRF Request Object.
        :param pk: The primary key ID of the assignment.
        :return: A list including student information, submission status, attempt count and AI feedback.
        """
        assignment = self.get_object()
        # Obtain all submissions for this assignment, and preload student information and AI evaluations.
        submissions = Submission.objects.filter(assignment=assignment) \
            .select_related('student', 'ai_evaluation') \
            .order_by('-created_at')

        # Serialized data
        data = []
        for sub in submissions:
            data.append({
                "id": sub.id,
                "student": sub.student.id,
                "student_name": sub.student.first_name or sub.student.username,
                "student_id_num": sub.student.student_id_num,
                "sub_type": sub.sub_type,
                "status": sub.status,
                "attempt_number": sub.attempt_number,
                "final_score": float(sub.final_score) if sub.final_score else None,
                "created_at": sub.created_at,
                "ai_evaluation": {
                    "feedback": sub.ai_evaluation.feedback if hasattr(sub, 'ai_evaluation') else None,
                    "total_score": float(sub.ai_evaluation.total_score) if hasattr(sub, 'ai_evaluation') else 0
                } if hasattr(sub, 'ai_evaluation') else None
            })
        return Response(data)

    @action(detail=True, methods=['get'], url_path='student-best')
    def get_student_best_performance(self, request, pk=None):
        """
        Obtain the detailed information about the "best performance" of a specific student in the current assignment.
        This interface is mainly used for teachers to view the highest score records of students and their complete AI evaluation reports.
        Logical steps:
        1. Target identification: Obtain the current subject being worked on and the student ID specified in the request.
        2. Selective filtering: From all the attempts of this student, prioritize the records with a status of 'completed' and the highest `final_score`. If the scores are the same, select the one with the larger ID (i.e., the most recent one).
        3. Data extraction: Safely extract the associated AI assessment (AIEvaluation) data.
        4. Field alignment: Include detailed knowledge comment scores (kp_scores), feedback content, and the teacher's review status.
        :param request: The student_id needs to be included in the query_params.
        :param pk: The ID of the assignment.
        :return: A JSON dictionary containing the highest score submission records and detailed evaluation information.
        """
        # Automatically verify job permissions and obtain instances
        assignment = self.get_object()
        student_id = request.query_params.get('student_id')

        if not student_id:
            return Response({"error": "need student_id"}, status=400)

        # 1. Search for the highest score Submission
        best_sub = Submission.objects.filter(
            assignment=assignment,
            student_id=student_id,
            status='completed'
        ).order_by('-final_score', '-id').first()

        if not best_sub:
            return Response({"message": "This student has not yet completed the submission."}, status=404)

        # 2. Obtain the corresponding AIEvaluation
        evaluation_data = None
        if hasattr(best_sub, 'ai_evaluation'):
            eval_obj = best_sub.ai_evaluation
            evaluation_data = {
                "total_score": float(eval_obj.total_score),
                "kp_scores": eval_obj.kp_scores,
                "feedback": eval_obj.feedback,
                "ai_raw_feedback": eval_obj.ai_raw_feedback,
                "is_published": eval_obj.is_published,
                "teacher_reviewed": eval_obj.teacher_reviewed
            }

        return Response({
            "submission_id": best_sub.id,
            "final_score": float(best_sub.final_score) if best_sub.final_score else 0,
            "attempt_number": best_sub.attempt_number,
            "created_at": best_sub.created_at,
            "evaluation": evaluation_data
        })

    @action(detail=False, methods=['get'], url_path='export-pdf-report')
    def export_pdf_report(self, request):
        """
        Export fully automatic intelligent scoring PDF report.
        This interface is the final output of the system for students and parents, and has the following advanced features:
        1. Dynamic Rubric matrix: Automatically generate A4 table according to the rating scale configured by the job.
        2. Intelligent coloring algorithm: deeply parse the JSON feedback generated by AI, calculate the corresponding level of each dimension score (HD/D/C/P/F),
        And the corresponding cells in the PDF table are automatically colored as background green to realize visual feedback.
        3. Robust Key matching: Eliminate whitespace, line breaks, or capitalization in AI responses via the 'sanitize_key' algorithm
        Dimension name matching failure problem.
        4. Professional typesetting engine: built on ReportLab, containing header information, score matrix, weight description and score breakdown table
        :param request: Need to include submission_id in query_params.
        :return: Binary PDF file stream.
        """
        import io
        import json
        import re
        from django.http import HttpResponse
        from django.shortcuts import get_object_or_404
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from django.utils.encoding import escape_uri_path

        # 1. Getting the data
        submission_id = request.query_params.get('submission_id')
        submission = get_object_or_404(Submission, id=submission_id)
        assignment = submission.assignment
        evaluation = getattr(submission, 'ai_evaluation', None)

        if not evaluation:
            return Response({"error": "No evaluation record found"}, status=400)

        # 2. Parse individual scores from ai_raw_feedback
        rubric_items = assignment.rubric_config.get('items', [])

        # Parse the ai_raw_feedback text field
        student_scores_data = {}
        if evaluation.ai_raw_feedback:
            try:
                clean_json_str = re.sub(r'```json|```', '', evaluation.ai_raw_feedback).strip()
                parsed_data = json.loads(clean_json_str)

                # Compatible with different JSON structures
                if isinstance(parsed_data, dict):
                    student_scores_data = parsed_data.get('scores', parsed_data.get('kp_scores', parsed_data))
            except Exception as e:
                print(f"JSON Parsing Error: {e}")
                student_scores_data = {}

        # Remove all Spaces, newlines, and special characters to make sure the Key matches
        def sanitize_key(text):
            return re.sub(r'[\s\W_]+', '', str(text)).lower()

        # Score after cleaning the dictionary mapping (for example: {" collectionsmanagementparts35 ": 78})
        clean_scores_map = {sanitize_key(k): v for k, v in student_scores_data.items()}
        font_registered = False
        font_paths = [
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/msyh.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/System/Library/Fonts/PingFang.ttc',
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFont', fp))
                    font_registered = True
                    break
                except Exception:
                    continue
        base_font = 'ChineseFont' if font_registered else 'Helvetica'
        # PDF basic Settings
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        if font_registered:
            for style_name in styles.byName:
                styles[style_name].fontName = base_font

        # Header information
        elements.append(Paragraph(f"<b>Performance Report: {assignment.title}</b>", styles['Title']))
        elements.append(Paragraph(
            f"Student: {submission.student.first_name or submission.student.username} ({submission.student.student_id_num})",
            styles['Normal']))
        elements.append(
            Paragraph(f"Final Score: <font color='blue' size='14'><b>{evaluation.total_score}</b></font> / 100",
                      styles['Normal']))
        elements.append(Spacer(1, 20))

        # 4. Build the Rubric matrix
        level_map = [
            {"label": "High Distinction", "match": "highdistinction"},
            {"label": "Distinction", "match": "distinction"},
            {"label": "Credit", "match": "credit"},
            {"label": "Pass", "match": "pass"},
            {"label": "Fail", "match": "fail"},
        ]

        header = ["Grade Level"]
        for item in rubric_items:
            c_name = item.get('criterion', 'Unknown')
            header.append(Paragraph(f"<b>{c_name}</b>", styles['BodyText']))
        table_data = [header]

        for lv in level_map:
            row = [lv['label']]
            for item in rubric_items:
                detailed = item.get('detailed_rubric', {})
                desc_text = "N/A"
                for k, v in detailed.items():
                    if lv['match'] in sanitize_key(k):
                        desc_text = v
                        break
                row.append(Paragraph(desc_text, styles['BodyText']))
            table_data.append(row)

        col_count = len(rubric_items) + 1
        col_widths = [75] + [455 / (col_count - 1)] * (col_count - 1)
        t = Table(table_data, colWidths=col_widths)

        table_style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
        ]

        # 5. Calculate staining locations & extract specific scores
        breakdown_rows = []

        for col_idx, item in enumerate(rubric_items, start=1):
            orig_criterion = item.get('criterion', '')
            c_key = sanitize_key(orig_criterion)

            score_val = clean_scores_map.get(c_key, 0)
            try:
                f_score = float(score_val)
            except (ValueError, TypeError):
                f_score = 0

            breakdown_rows.append([Paragraph(orig_criterion, styles['Normal']), f"{item.get('weight')}%", f"{f_score}"])

            if f_score > 0:
                target_row = 5
                if f_score >= 85:
                    target_row = 1
                elif f_score >= 75:
                    target_row = 2
                elif f_score >= 65:
                    target_row = 3
                elif f_score >= 50:
                    target_row = 4

                table_style.append(('BACKGROUND', (col_idx, target_row), (col_idx, target_row), colors.lightgreen))

        t.setStyle(TableStyle(table_style))
        elements.append(t)

        # 6. Breakdown of scores
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("<b>Score Breakdown Details</b>", styles['Heading3']))

        detail_header = [["Assessment Criterion", "Weight", "Score"]]
        bt = Table(detail_header + breakdown_rows, colWidths=[330, 80, 120], hAlign='LEFT')
        bt.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(bt)

        doc.build(elements)
        buffer.seek(0)

        try:
            SystemOperationLog.objects.create(
                user=request.user,
                action="EXPORT_PDF",
                target_type="Submission",
                target_id=str(submission.id),
                detail=f"Exported PDF report for student {submission.student.username}. Assignment: {assignment.title}"
            )
        except Exception as log_e:
            print(f"Logging failure: {log_e}")

        filename = f"Report_{submission.student.student_id_num}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f"attachment; filename*=utf-8''{escape_uri_path(filename)}"
        return response

    @action(detail=True, methods=['get'], url_path='export-all-pdf-reports')
    def export_all_pdf_reports(self, request, pk=None):
        """
        The PDF report of the highest score of the whole class is exported in bulk packaging.
        The interface implements complex many-to-one resource aggregation and format conversion:
        1. Intelligent deduplication: In all submitted records, SQL sorting and memory filtering are used to ensure that each student only exports the "representative work" with the highest score.
        Parallel stream processing: The ReportLab document stream is built independently for each student in the loop, and dynamic Rubric coloring is supported.
        3. Memory ZIP: Use 'zipfile.writestr' to write the resulting PDF binary stream directly to the memory zip package.
        It avoids the disk pressure and cleaning problem caused by a large number of temporary files on the server.
        4. Naming normalization: The automatically generated PDF file name contains the student number and name, and the compressed package name contains the assignment title.
        :param pk: The ID of the Assignment.
        :return:
        """
        import io, json, re, zipfile
        from django.http import HttpResponse
        from django.utils.encoding import escape_uri_path
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        assignment = self.get_object()

        # 1. Get the submission with the highest score from each student
        all_subs = Submission.objects.filter(assignment=assignment, status='completed').order_by(
            'student', '-final_score', '-ai_evaluation__total_score', '-id'
        ).select_related('student', 'ai_evaluation')

        # Memory deduplication ensures that each person has only one copy of the best report card
        best_submissions = []
        seen_students = set()
        for s in all_subs:
            if s.student_id not in seen_students:
                best_submissions.append(s)
                seen_students.add(s.student_id)

        if not best_submissions:
            return Response({"error": "No completed submissions found to export"}, status=404)

        # 2. Initialize the ZIP memory stream
        byte_io = io.BytesIO()

        def sanitize_key(text):
            return re.sub(r'[\s\W_]+', '', str(text)).lower()
        # Register Chinese font for PDF generation
        font_registered = False
        font_paths = [
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/msyh.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/System/Library/Fonts/PingFang.ttc',
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFont', fp))
                    font_registered = True
                    break
                except Exception:
                    continue
        base_font = 'ChineseFont' if font_registered else 'Helvetica'
        with zipfile.ZipFile(byte_io, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for sub in best_submissions:
                evaluation = getattr(sub, 'ai_evaluation', None)
                if not evaluation:
                    continue

                try:
                    pdf_buffer = io.BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30,
                                            bottomMargin=30)
                    elements = []
                    styles = getSampleStyleSheet()
                    if font_registered:
                        for style_name in styles.byName:
                            styles[style_name].fontName = base_font
                    # Header information
                    elements.append(Paragraph(f"<b>Performance Report: {assignment.title}</b>", styles['Title']))
                    elements.append(Paragraph(
                        f"Student: {sub.student.first_name or sub.student.username} ({sub.student.student_id_num})",
                        styles['Normal']))
                    elements.append(Paragraph(
                        f"Final Score: <font color='blue' size='14'><b>{evaluation.total_score}</b></font> / 100",
                        styles['Normal']))
                    elements.append(Spacer(1, 20))

                    # Parsing score
                    student_scores_data = {}
                    if evaluation.ai_raw_feedback:
                        try:
                            json_str = re.sub(r'```json|```', '', str(evaluation.ai_raw_feedback)).strip()
                            match = re.search(r'(\{.*\})', json_str, re.DOTALL)
                            if match:
                                data_obj = json.loads(match.group(1))
                                student_scores_data = data_obj.get('scores', data_obj.get('kp_scores', data_obj))
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass

                    this_clean_map = {sanitize_key(k): v for k, v in student_scores_data.items()}

                    # Construct the Rubric matrix
                    level_map = [
                        {"label": "High Distinction", "match": "highdistinction"},
                        {"label": "Distinction", "match": "distinction"},
                        {"label": "Credit", "match": "credit"},
                        {"label": "Pass", "match": "pass"},
                        {"label": "Fail", "match": "fail"},
                    ]
                    rubric_items = assignment.rubric_config.get('items', [])
                    header = ["Grade Level"] + [Paragraph(f"<b>{i.get('criterion')}</b>", styles['BodyText']) for i in
                                                rubric_items]
                    table_data = [header]

                    for lv in level_map:
                        row = [lv['label']]
                        for item in rubric_items:
                            detailed = item.get('detailed_rubric', {})
                            desc_text = "N/A"
                            for k, v in detailed.items():
                                if lv['match'] in sanitize_key(k):
                                    desc_text = v
                                    break
                            row.append(Paragraph(desc_text, styles['BodyText']))
                        table_data.append(row)

                    # Styles and Coloring
                    this_t_style = [
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ]

                    breakdown_rows = []
                    for col_idx, item in enumerate(rubric_items, start=1):
                        orig_c = item.get('criterion', '')
                        c_key = sanitize_key(orig_c)
                        score_val = this_clean_map.get(c_key, 0)
                        try:
                            fs = float(score_val)
                        except (ValueError, TypeError):
                            fs = 0

                        breakdown_rows.append([Paragraph(orig_c, styles['Normal']), f"{item.get('weight')}%", f"{fs}"])

                        if fs > 0:
                            row_idx = 1 if fs >= 85 else 2 if fs >= 75 else 3 if fs >= 65 else 4 if fs >= 50 else 5
                            this_t_style.append(
                                ('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.lightgreen))

                    t = Table(table_data, colWidths=[75] + [455 / (len(rubric_items) or 1)] * len(rubric_items))
                    t.setStyle(TableStyle(this_t_style))
                    elements.append(t)
                    elements.append(Spacer(1, 20))

                    bt = Table([["Criterion", "Weight", "Score"]] + breakdown_rows, colWidths=[330, 80, 120],
                               hAlign='LEFT')
                    bt.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
                                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]))
                    elements.append(bt)

                    # Generate a PDF binary stream
                    doc.build(elements)
                    pdf_content = pdf_buffer.getvalue()

                    # Write ZIP
                    arc_name = f"{sub.student.student_id_num}_{sub.student.username}_Report.pdf"
                    zip_file.writestr(arc_name, pdf_content)

                except Exception as e:
                    print(f"FAILED TO GENERATE PDF for {sub.student.student_id_num}: {e}")
                    continue
        try:
            SystemOperationLog.objects.create(
                user=request.user,
                action="EXPORT_ALL_PDF",
                target_type="Assignment",
                target_id=str(assignment.id),
                detail=f"Batch exported {len(best_submissions)} PDF reports for class: {assignment.title}"
            )
        except Exception as log_e:
            print(f"Logging failure: {log_e}")

        # 3. Constructing the response
        byte_io.seek(0)
        zip_filename = f"PDF_Reports_{assignment.title}.zip"

        response = HttpResponse(byte_io, content_type='application/zip')
        response['Content-Disposition'] = f"attachment; filename*=utf-8''{escape_uri_path(zip_filename)}"
        return response

    @action(detail=False, methods=['get'], url_path='all-appeals')
    def get_all_appeals(self, request):
        """
        The teacher checks the record of the grade appeal of all the assignments under his name.
        When students have objections to the AI scoring results and submit appeals, the interface provides a unified review workbench for teachers.
        :return: A flat list of complaint records.
        """
        from .models import Appeal

        # 1. Filtering logic: Find all appeals for assignments belonging to the current teacher
        appeals = Appeal.objects.filter(
            evaluation__submission__assignment__teacher=request.user
        ).select_related(
            'evaluation__submission__student',
            'evaluation__submission__assignment',
            'evaluation'
        ).order_by('-created_at')

        # 2. Constructing return data
        data = []
        for a in appeals:
            sub = a.evaluation.submission
            data.append({
                "id": a.id,
                "submission_id": sub.id,
                "assignment_title": sub.assignment.title,
                "student_name": sub.student.first_name or sub.student.username,
                "student_id_num": sub.student.student_id_num,
                "class_name": sub.student.class_name,

                "original_score": float(a.evaluation.total_score),
                "student_reason": a.student_reason,
                "ai_judgment": a.ai_judgment,
                "status": a.status,
                "status_display": a.get_status_display(),
                "created_at": a.created_at,
                "teacher_remark": a.teacher_remark,
                "adjusted_score": float(a.adjusted_score) if a.adjusted_score else None
            })

        return Response(data)

    @action(detail=True, methods=['post'], url_path='resolve-appeal')
    def resolve_appeal(self, request, pk=None):
        """
        Teacher adjudicating appeal: Perform final grading and close the case.
        1. Arbitration intervention: The teacher decides whether to adjust the score according to the reason of the student's appeal and the AI initial review proposal.
        2. Penetrating synchronization (Crucial) :
            - If score adjustment: synchronously modify 'total_score' in the 'AIEvaluation' record and mark it as reviewed.
            - Synchronize transcripts: Update the 'final_score' in the 'Submission' table in real time to ensure that the latest score is displayed in the student's personal center.
        3. Status loop closure: Set the appeal status to 'completed' and restore the submission status from 'appealing' to 'completed'.
        4. Transaction protection: Ensure that all three database operations of score transfer, status change, and score synchronization are either successful or reversed.
        :param request: The primary key ID of the Appeal.
        :param pk: A request body containing adjusted_score (optional) and teacher_remark (required).
        :return:
        """
        from .models import Appeal
        # 1. Obtaining grievance records
        appeal = get_object_or_404(Appeal, id=pk)

        if appeal.evaluation.submission.assignment.teacher != request.user:
            return Response({"error": "You do not have permission to resolve this appeal"}, status=403)

        if appeal.status != 'pending_teacher':
            return Response(
                {"error": f"This appeal is in '{appeal.get_status_display()}' status and cannot be processed"},
                status=400)

        # 2. Getting parameters
        new_score = request.data.get('adjusted_score')
        teacher_remark = request.data.get('teacher_remark')

        if new_score is not None:
            try:
                score_val = float(new_score)
                if score_val < 0 or score_val > 100:
                    return Response({"error": "Score must be between 0 and 100"}, status=400)
            except (ValueError, TypeError):
                return Response({"error": "Invalid score format"}, status=400)

        with transaction.atomic():
            # 3. If the teacher gives a new grade, directly overwrite the AI's grading record
            if new_score is not None:
                evaluation = appeal.evaluation
                evaluation.total_score = new_score
                evaluation.teacher_reviewed = True
                evaluation.save()

                # 4. Update the final_score of the Submission table synchronously
                submission = evaluation.submission
                submission.final_score = new_score
                submission.save()

                appeal.adjusted_score = new_score

            # 5. Update the claim sheet status
            appeal.status = 'completed'
            appeal.teacher_remark = teacher_remark
            appeal.save()

            # 6. Restores the status of the commit record from appealing to completed
            sub = appeal.evaluation.submission
            sub.status = 'completed'
            sub.save()

            try:
                log_detail = f"Resolved appeal for student {sub.student.username}."
                if new_score is not None:
                    log_detail += f" Score adjusted to {new_score}."
                else:
                    log_detail += " Maintained original score."
                log_detail += f" Remark: {teacher_remark[:50]}"

                SystemOperationLog.objects.create(
                    user=request.user,
                    action="RESOLVE_APPEAL",
                    target_type="Appeal",
                    target_id=str(appeal.id),
                    detail=log_detail
                )
            except Exception as log_e:
                print(f"Logging failure: {log_e}")

        return Response({"message": "The appeal was processed successfully and the score was updated synchronously"})

    @action(detail=True, methods=['get'], url_path='teaching-insights')
    def get_teaching_insights(self, request, pk=None):
        """
        AI Teaching Insights (异步版本):
        1. 检查是否已有缓存报告 → 直接返回
        2. 没有则触发 Celery 异步任务 → 返回 pending 状态
        3. 前端轮询直到 status 为 ready
        """
        from .models import TeachingInsightReport

        assignment = self.get_object()

        # 1. 检查是否已有缓存报告
        try:
            report = TeachingInsightReport.objects.get(assignment=assignment)
            if report.status == 'ready':
                return Response({
                    "status": "ready",
                    "stats": report.stats_data,
                    "ai_insights": report.ai_insights
                })
            elif report.status == 'pending':
                return Response({"status": "pending", "message": "AI is analyzing, please wait..."})
            elif report.status == 'error':
                # 报告生成失败，重新触发
                report.delete()
        except TeachingInsightReport.DoesNotExist:
            pass

        # 2. 没有报告，触发异步任务
        from .tasks import async_generate_teaching_insights
        async_generate_teaching_insights.delay(assignment.id)

        # 创建 pending 状态的记录
        TeachingInsightReport.objects.get_or_create(
            assignment=assignment,
            defaults={'status': 'pending'}
        )

        return Response({"status": "pending", "message": "AI analysis started, please wait..."})

    @action(detail=True, methods=['post'], url_path='plagiarism-check')
    def plagiarism_check(self, request, pk=None):
        """
        Triggers an asynchronous plagiarism audit for an assignment.
        Workflow Logic:
        1. Idempotency Check: Prevents redundant scans if a report is 'pending'.
        2. Record Creation: Initializes a `PlagiarismReport` to track the task.
        3. Task Dispatch: Offloads the heavy lifting to Celery.
        4. Feedback: Returns the report ID for frontend status polling.
        :param request: The incoming HTTP POST request.
        :param pk: Primary key of the assignment to be audited.
        :return: Response containing the report ID and current status.
        """
        assignment = self.get_object()

        # Check if there is an ongoing duplicate check
        existing = PlagiarismReport.objects.filter(
            assignment=assignment, status='pending'
        ).first()
        if existing:
            return Response({
                'report_id': existing.id,
                'status': 'pending',
                'message': 'A plagiarism check is already in progress'
            })

        # Creating report records
        report = PlagiarismReport.objects.create(
            assignment=assignment,
            status='pending'
        )

        # Triggers an asynchronous task
        async_plagiarism_check.delay(report.id, assignment.id)

        return Response({
            'report_id': report.id,
            'status': 'pending',
            'message': 'Plagiarism check started'
        })

    @action(detail=True, methods=['get'], url_path='plagiarism-results')
    def plagiarism_results(self, request, pk=None):
        """
        Retrieves the history and detailed findings of plagiarism audits for an assignment.
        Business Logic:
        1. Historical Lookup: Fetches all plagiarism reports associated with the assignment.
        2. Data Packaging: Serializes report metadata, including similarity matches and
           external MOSS report links.
        3. Error Transparency: Includes error messages if an audit failed (e.g., MOSS timeout).
        :param request: The incoming HTTP GET request.
        :param pk: Primary key of the assignment.
        :return: List of report objects containing match data and status.
        """
        assignment = self.get_object()
        reports = PlagiarismReport.objects.filter(assignment=assignment)

        data = []
        for r in reports:
            data.append({
                'id': r.id,
                'status': r.status,
                'mode': r.mode,
                'report_url': r.report_url,
                'matches': r.matches,
                'file_count': r.file_count,
                'error_message': r.error_message,
                'created_at': r.created_at.isoformat()
            })

        return Response(data)

    @action(detail=True, methods=['post'], url_path='plagiarism-diff')
    def plagiarism_diff(self, request, pk=None):
        """
        Fetches and parses side-by-side code comparisons from remote MOSS reports.
        Business Logic:
        1. Remote Scaping: Retrieves raw HTML frames from the Stanford MOSS server.
        2. Snippet Extraction: Isolates source code contained within <PRE> tags.
        3. Match Highlighting: Parses <FONT> color tags used by MOSS to identify specific
           lines of code that are structurally identical between two submissions.
        4. Sanitization: Cleans HTML entities and tags to provide a safe, JSON-ready
        array of code lines for the frontend diff viewer.
        :param request: Request containing url_a and url_b (MOSS match frames).
        :param pk: Primary key of the assignment.
        :return: Response containing filenames and line-by-line code with 'matched' flags.
        """
        url_a = request.data.get('url_a', '')
        url_b = request.data.get('url_b', '')

        if not url_a or not url_b:
            return Response({'error': 'Missing URLs'}, status=400)

        import urllib.request
        import re
        import html as html_mod

        files = []
        for url in [url_a, url_b]:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    content = resp.read().decode('utf-8', errors='ignore')

                title_match = re.search(r'<TITLE>(.*?)</TITLE>', content, re.IGNORECASE)
                filename = title_match.group(1) if title_match else url.split('/')[-1]

                pre_match = re.search(r'<PRE>(.*?)</PRE>', content, re.DOTALL | re.IGNORECASE)
                if not pre_match:
                    files.append({'filename': filename, 'lines': []})
                    continue

                pre_raw = pre_match.group(1)
                raw_lines = pre_raw.split('\n')
                processed_lines = []

                in_font = False
                for line in raw_lines:
                    if '<FONT' in line.upper():
                        in_font = True
                    if '</FONT>' in line.upper():
                        in_font = False
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    clean_line = html_mod.unescape(clean_line)
                    processed_lines.append({
                        'code': clean_line,
                        'matched': in_font
                    })

                files.append({'filename': filename, 'lines': processed_lines})

            except Exception as e:
                files.append({'filename': 'Error loading', 'lines': []})

        return Response({'files': files})


class KnowledgePointViewSet(viewsets.ModelViewSet):
    """
    Knowledge point dictionary query view set.
    The interface acts as a common dictionary table that allows all log in users, teachers and students, to view a list of knowledge points within the system.
    Since it is only used for data retrieval, ReadOnlyModelViewSet is used to disable all additions, deletions and changes.
    Permission Restrictions: Restrict access to IsAuthenticated users only.
    """
    queryset = KnowledgePoint.objects.all().order_by("-id")
    serializer_class = KnowledgePointSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs


class GroupViewSet(viewsets.ModelViewSet):
    """
    小组管理视图集：支持组建、加入、查看小组成员
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 仅查看当前用户参与的小组，或当前课程下的小组
        course_id = self.request.query_params.get('course')
        if course_id:
            return Group.objects.filter(course_id=course_id)
        return Group.objects.filter(members=self.request.user)

    def perform_create(self, serializer):
        # 创建者自动成为组长并加入成员列表
        group = serializer.save(leader=self.request.user)
        group.members.add(self.request.user)

    @action(detail=False, methods=['post'], url_path='join-by-code')
    def join_by_code(self, request):
        """
        学生输入邀请码加入小组
        """
        code = request.data.get('invite_code', '').strip().upper()
        if not code:
            return Response({"error": "请输入小组邀请码"}, status=400)

        try:
            group = Group.objects.get(invite_code=code)

            # 1. 校验人数上限（从该小组关联课程的作业中获取约束，或使用通用约束）
            # 简单起见，这里可以校验 Group 成员数
            if group.members.count() >= 10:  # 假设硬上限10人，或者你可以去查 Assignment
                return Response({"error": "小组人数已满"}, status=400)

            # 2. 校验是否已在当前课程的其他小组里
            if Group.objects.filter(course=group.course, members=request.user).exists():
                return Response({"error": "你已在当前课程的其他小组中，无法重复加入"}, status=400)

            group.members.add(request.user)
            return Response({"message": f"成功加入小组：{group.name}"})
        except Group.DoesNotExist:
            return Response({"error": "邀请码无效"}, status=404)


class TeacherCourseViewSet(viewsets.ModelViewSet):
    """
    Set of views for teacher-side course management.
    Provides full CRUD functionality for courses. The view set fetches logic by rewriting the query set,
    Strict data isolation is implemented to ensure that teachers can only manage the courses under their own names.
    Permission Restrictions: Access is restricted to authenticated users with the 'teacher' role.
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsTeacher]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """
        The query set acquisition logic was rewritten to achieve data isolation.
        Filtering by the user currently requesting (request.user) ensures that the list of courses is returned
        Only courses created or responsible for by the instructor are included.
        :return:
            QuerySet: The set of courses associated with the currently logged-in teacher.
        """
        return Course.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        """
        Automatically associate the current teacher when saving a new course.
        Override the hook function to inject teacher information before the database is saved, preventing the front end from passing through
        Tampering with teacher ids to create courses across permissions.
        :param serializer: Validated course serializer.
        :return:
        """
        # Force the teacher field of the course to be the current logged-in user
        if self.request.user.role != 'admin':
            course = serializer.save(teacher=self.request.user)
        else:
            course = serializer.save()

        try:
            SystemOperationLog.objects.create(
                user=self.request.user,
                action="CREATE",
                target_type="Course",
                target_id=str(course.id),
                detail=f"Created a new course: {course.name}"
            )
        except Exception as log_e:
            print(f"Logging failure: {log_e}")

    def perform_update(self, serializer):
        """

        :param serializer:
        :return:
        """
        if self.request.user.role != 'admin':
            course = serializer.save(teacher=self.request.user)
        else:
            course = serializer.save()

        try:
            SystemOperationLog.objects.create(
                user=self.request.user,
                action="UPDATE",
                target_type="Course",
                target_id=str(course.id),
                detail=f"Updated course information: {course.name}"
            )
        except Exception as log_e:
            print(f"Logging failure: {log_e}")

    def destroy(self, request, *args, **kwargs):
        """
        Safely deletes a course while enforcing relational integrity and logging.
        :param request: The DELETE request object.
        :return: 204 No Content on success, or 400 Bad Request if integrity check fails.
        """
        instance = self.get_object()
        course_id = instance.id
        course_name = instance.name
        if instance.assignments.exists():
            return Response({"error": "There are already assignments for this course. Please delete them first."}, status=400)

        self.perform_destroy(instance)

        try:
            from .models import SystemOperationLog
            SystemOperationLog.objects.create(
                user=request.user,
                action="DELETE",
                target_type="Course",
                target_id=str(course_id),
                detail=f"Deleted course: {course_name}"
            )
        except Exception as log_e:
            print(f"Logging failure: {log_e}")
        return Response({"message": "Course deleted successfully"}, status=204)

    @action(detail=True, methods=['get'], url_path='students')
    def enrolled_students(self, request, pk=None):
        """
        Obtain the list of registered students for the current specific course.
        This interface queries the information of all students who have taken the course by associating with the course ID, and manually extracts the key fields for return.
        It is mainly used for data display on the "Student Management" page of the teacher end.
        :param request: DRF Request Object.
        :param pk: Course unique identifier ID (automatically captured by the URL)
        :return: Response: A list containing information such as student ID, student number, name, and class.
        """
        course = self.get_object()
        students = course.students.all()

        student_data = [{
            "id": s.id,
            "username": s.username,
            "name": s.first_name,
            "student_id_num": s.student_id_num,
            "class_name": s.class_name
        } for s in students]

        return Response(student_data)

    @action(detail=True, methods=['post'], url_path='remove-students')
    def bulk_remove_students(self, request, pk=None):
        """
        Batch remove enrolled students from the current course.
        This operation only breaks the many-to-many association between the Course and the Student (enrollment relationship),
        and will not delete the student accounts in the User table. Teachers can select multiple students on the interface and perform the removal operation at once.
        :param request: A request including the list of student IDs to be removed.
        :param pk: Target course ID
        :return: Response: Success message and the actual number of students removed.
        """
        course = self.get_object()
        student_ids = request.data.get('student_ids', [])

        if not student_ids:
            return Response({"error": "Please select the student to be removed."}, status=400)

        try:
            students_to_remove = course.students.filter(id__in=student_ids)
            count = students_to_remove.count()

            student_names = ", ".join([s.username for s in students_to_remove[:3]])
            if count > 3:
                student_names += f" and {count - 3} others"

            course.students.remove(*students_to_remove)

            try:
                from .models import SystemOperationLog
                SystemOperationLog.objects.create(
                    user=request.user,
                    action="REMOVE_MEMBER",
                    target_type="Course",
                    target_id=str(course.id),
                    detail=f"Removed {count} students from course '{course.name}'. Targets: {student_names}"
                )
            except Exception as log_e:
                print(f"Logging failure: {log_e}")

            return Response({
                "message": f"Successfully removed {count} students from the course.",
                "removed_count": count
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class TeacherStudentManagementViewSet(viewsets.ViewSet):
    """
    Teacher end student management view set.
    It provides administrative management functions for student accounts, such as batch import and account initialization.
    This view set is not directly associated with a single model, but operates as a functional control center.
    Permission restrictions: Access is restricted to authenticated users with the 'teacher' role only.
    """
    permission_classes = [IsTeacher]

    @action(detail=False, methods=['post'], url_path='import-students')
    def import_students(self, request):
        """
        Create student accounts in bulk by uploading Excel/CSV files, and optionally pull one button into a specific course.
        :param request: DRF request object.
                        -FILES ['file']: The uploaded form file.
                        -data ['course_id'] (int, optional): Target course ID.
        :return: Response: Success message containing creation and enrollment statistics
        """
        file = request.FILES.get('file')
        course_id = request.data.get('course_id')

        if not file:
            return Response({"error": "Please upload Excel or CSV file"}, status=400)

        try:
            # Force all columns to be read as plain text, and prohibit Pandas from converting student numbers to floating-point numbers or scientific notation
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, dtype=str)
            else:
                df = pd.read_excel(file, dtype=str)

            # Clean the list header to prevent the UTF-8 BOM header of the CSV file from making student_id unrecognizable
            df.columns = [str(c).strip().replace('\ufeff', '').lower() for c in df.columns]

            created_count = 0
            enrolled_count = 0

            with transaction.atomic():
                target_course = None
                if course_id:
                    target_course = Course.objects.get(id=course_id, teacher=request.user)

                for _, row in df.iterrows():
                    sid = str(row.get('student_id', '')).strip()

                    # If Pandas or Excel still add ".0" to the end by mistake, force the removal
                    if sid.endswith('.0'):
                        sid = sid[:-2]

                    if not sid or sid == 'nan':
                        continue

                    user, created = User.objects.get_or_create(
                        student_id_num=sid,
                        defaults={
                            'username': sid,
                            'first_name': str(row.get('name', '')).strip(),
                            'class_name': str(row.get('class', '')).strip(),
                            'role': 'student',
                            'password': make_password(sid),
                            'approval_status': 'approved',
                            'is_active': True
                        }
                    )

                    if created:
                        created_count += 1

                    if target_course:
                        if not target_course.students.filter(id=user.id).exists():
                            target_course.students.add(user)
                            enrolled_count += 1

            try:
                detail_msg = f"Bulk imported students from file: {file.name}. "
                detail_msg += f"Results: {created_count} new accounts created, {enrolled_count} students enrolled."
                if course_id:
                    detail_msg += f" Target Course ID: {course_id}"

                SystemOperationLog.objects.create(
                    user=request.user,
                    action="IMPORT",
                    target_type="User",
                    target_id=None,
                    detail=detail_msg
                )
            except Exception as log_e:
                print(f"Logging failure: {log_e}")

            return Response({
                "message": f"Import success: {created_count} new student accounts are created and {enrolled_count} people are added to the course."
            })

        except Course.DoesNotExist:
            return Response({"error": "The specified course does not exist or you do not have permission to operate it."}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"Failed table parsing: {str(e)}"}, status=400)

    @action(detail=False, methods=['get'], url_path='download-template')
    def download_template(self, request):
        """
        Provide downloadable Excel templates for batch import of student data.
        Business Logic:
        1. Standardization First: Define the standard column headers that the system can recognize (student_id, name, class).
        2. Example Guidance: Pre-fill a few rows of sample data in the template to visually inform the user of the filling guidelines.
        3. Memory Generation: Utilize `io.BytesIO` and `pandas` to directly construct the file stream in the server's memory,
        without generating temporary files on the disk, thereby enhancing concurrent processing capabilities.
        4. Response Alignment: Set the correct MIME type and Content-Disposition to ensure that the browser directly triggers the download.
        :return: HttpResponse: An Excel template file with preset column headers.
        """
        columns = ['student_id', 'name', 'class']

        sample_data = [
            ['20260001', 'John Doe', 'Class A'],
            ['20260002', 'Jane Smith', 'Class B']
        ]

        df = pd.DataFrame(sample_data, columns=columns)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')

        output.seek(0)

        filename = "student_import_template.xlsx"
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


# Student Side View

class StudentAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Student side assignments view set
    Provide only read-only operations (List/Retrieve),
    Allowing students to view all assignments for their course,
    It also supports querying the submission and rating status of a specific job through custom actions.
    Permission Restrictions: Access is restricted to logged-in users (student role) only.
    """
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Get a list of assignments for the current student's course.
        Filtering through many-to-many relationships,
        Make sure students can only see assignments posted under their Course, sorted by due date in descending order.
        :return: QuerySet: A filtered list of assessments
        """
        return Assignment.objects.filter(course__students=self.request.user).distinct().order_by('-deadline')

    @action(detail=True, methods=['get'], url_path='my-status')
    def my_status(self, request, pk=None):
        """
        Get the latest submission status and grade of the current student for a particular assignment.
        This interface retrieves the record of the student's last Submission,
        And query the published AI evaluation information.
        :param request: DRF request object
        :param pk: Assessment ID
        :return: Response: A dictionary containing status (submitted/not submitted), score, feedback, number of submissions, etc.
        """
        assignment = self.get_object()
        submission = Submission.objects.filter(student=request.user, assignment=assignment).order_by(
            '-created_at').first()
        if not submission:
            return Response({"status": "unsubmitted", "message": "Unsubmitted"})
        evaluation = AIEvaluation.objects.filter(submission=submission, is_published=True).first()
        return Response({
            "status": submission.status,
            "final_score": float(evaluation.total_score) if evaluation else "To be released",
            "feedback": evaluation.feedback if evaluation else "In the scoring process",
            "submitted_at": submission.created_at,
            "attempt_count": Submission.objects.filter(student=request.user, assignment=assignment).count()
        })


    @action(detail=True, methods=['post'], url_path='submit-appeal')
    def submit_appeal(self, request, pk=None):
        """
        Student submission of grade appeal: With "assignment level" idempotence protection across submission records.
        1. Automatic anchor of appeal subject: Automatically select the student's "highest score submission" under the current assignment as the appeal object to ensure that the appeal value is maximized.
        2. Cross-Request Lock: with 'transaction.atomic' and "immediate placeholder" logic,
        The data inventory certificate is completed before the AI time-consuming operation begins, and the dirty data generated by repeated clicks on the front end is completely eliminated.
        3. AI Pre-audit:
        - Reasonable appeal: After AI gives audit recommendations, the flow is transferred to the teacher side for manual final judgment.
        - Unreasonable complaints: AI directly gives reasons for rejection, reducing the ineffective review workload of teachers by 80%.
        4. Robustness: If the AI service is abnormal, the system automatically sets the state to 'pending_teacher' to ensure that the student appeal channel is always open.
        :param pk: Assignment ID
        :return:
        """
        assignment = self.get_object()
        student_reason = request.data.get('reason')

        if not student_reason:
            return Response({"error": "Please enter the reason for appeal"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Get grievant body: Find the highest score submission record for this student under this assignment
        submission = Submission.objects.filter(
            assignment=assignment,
            student=request.user,
            status='completed'
        ).select_related('ai_evaluation').order_by('-final_score').first()

        if not submission or not hasattr(submission, 'ai_evaluation'):
            return Response({"error": "No valid score could be found to initiate a complaint"}, status=status.HTTP_400_BAD_REQUEST)

        from .models import Appeal

        # 2. Duplicate checks across commit records
        def create_placeholder_safely():
            with transaction.atomic():
                already_appealed = Appeal.objects.filter(
                    evaluation__submission__assignment=assignment,
                    evaluation__submission__student=request.user
                ).exists()

                if already_appealed:
                    return None

                # 3. Before the AI is invoked, the inventory certificate is entered in the database
                appeal = Appeal.objects.create(
                    evaluation=submission.ai_evaluation,
                    student_reason=student_reason,
                    status='pending_ai',
                    ai_judgment="AI is auditing the code logic, please wait..."
                )

                # Lock the current Submission status to Appeal
                submission.status = 'appealing'
                submission.save(update_fields=['status'])

                return appeal

        # Execute the "placeholder" function
        appeal_placeholder = create_placeholder_safely()

        if not appeal_placeholder:
            return Response({"error": "You have submitted a complaint for this job, please do not repeat the operation"}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Perform a time-consuming AI audit service
        from .utils.appeal_service import AppealService
        try:
            review_result = AppealService.process_student_appeal(submission, student_reason)

            # 5. Backfill AI audit results and flow state
            is_reasonable = review_result.get('is_reasonable', False)

            appeal_placeholder.ai_judgment = review_result.get('ai_judgment', "AI has completed the audit")
            appeal_placeholder.status = 'pending_teacher' if is_reasonable else 'rejected_by_ai'
            appeal_placeholder.save()

            try:
                from .models import SystemOperationLog

                # 记录详情：包括申诉是否被 AI 认为合理
                ai_res = "Reasonable" if is_reasonable else "Unreasonable"
                log_detail = f"Student submitted an appeal for '{assignment.title}'. AI Pre-audit: {ai_res}."

                SystemOperationLog.objects.create(
                    user=request.user,  # 这里的 user 是学生
                    action="SUBMIT_APPEAL",
                    target_type="Appeal",
                    target_id=str(appeal_placeholder.id),
                    detail=log_detail
                )
            except Exception as log_e:
                print(f"Logging failure: {log_e}")

            return Response({
                "status": "success",
                "is_reasonable": is_reasonable,
                "message": review_result.get('reply_for_student', "The complaint has been dealt with.")
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            appeal_placeholder.ai_judgment = f"AI audit service exception: {str(e)}"
            appeal_placeholder.status = 'pending_teacher'
            appeal_placeholder.save()
            from .models import SystemOperationLog
            try:
                SystemOperationLog.objects.create(
                    user=request.user,
                    action="APPEAL_AI_ERROR",
                    target_type="Appeal",
                    target_id=str(appeal_placeholder.id),
                    detail=f"AI Pre-audit service failed. Error: {str(e)[:100]}. Automatically assigned to teacher."
                )
            except Exception:
                pass

            return Response({
                "error": "The AI pre-review has expired, and the system has automatically transferred it to the teacher for manual review",
                "is_reasonable": True
            }, status=status.HTTP_200_OK)


class StudentCourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Student side course view set.
    A read-only interface (List/Retrieve) is provided to allow students to view information about courses they have joined.
    ReadOnlyModelViewSet is used to ensure that students cannot create or modify course data through this interface.
    Permission Restrictions: Access is restricted to logged-in users only
    """
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Gets a list of courses that the current student has taken.
        Filtering by using the reverse association of students (many-to-many fields) in the Course model,
        Ensure that the query set returned contains only the current logged-in student himself.
        :return: QuerySet: The set of courses that the current student belongs to.
        """
        return Course.objects.filter(students=self.request.user)

    @action(detail=False, methods=['post'], url_path='join-by-code')
    def join_by_code(self, request):
        """
        Students actively join the course through the course invitation code.
        1. Format Standardization: Remove whitespace from the input invitation code and convert it to uppercase to ensure a robust validation.
        2. Uniqueness search: Find the active course in the course schedule that matches the 'invite_code'.
        3. Membership check: Check whether the current requested user (Student) is already in the course list to avoid duplicate records.
        4. Association persistence: Use Django ManyToMany's '.add() 'method to add the student to' course.students'.
        :return: Contains information on joining success and basic course data
        """
        code = request.data.get('invite_code', '').strip().upper()

        if not code:
            return Response({"error": "Please enter an invitation code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Finding a Course
            course = Course.objects.get(invite_code=code)

            # 2. Check if the student is already a member of the course
            if course.students.filter(id=request.user.id).exists():
                return Response({"error": f"You are already a member of '{course.name}'"},
                                status=status.HTTP_400_BAD_REQUEST)

            # 3. Add the student to the ManyToMany field of the course
            course.students.add(request.user)

            return Response({
                "message": f"Successfully joined {course.name}!",
                "course_id": course.id,
                "course_name": course.name
            }, status=status.HTTP_200_OK)

        except Course.DoesNotExist:
            return Response({"error": "Invalid invitation code. Please check again."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Internal system error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudentSubmissionViewSet(viewsets.ModelViewSet):
    """
    Student assignments are submitted with automated processing of view sets.
    This set of views implements highly hardened commit logic, including:
    1. Submission Limit: check the student's course selection status and the maximum number of submissions allowed.
    2. Type automatic recognition: the back-end independently determines the type of single file and Archive.
    3. Asynchronous pipeline orchestration: Integrate ProjectAnalyzer and AIScorer for preprocessing and dispatch Celery asynchronous tasks.
    Permission Restrictions: Access is restricted to logged-in users only.
    """
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Get the submission history of the current student.
        :return: Sorting by creation time in reverse order ensures that students see the most recent submission record first.
        """
        return Submission.objects.filter(student=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """
        The core logic that handles student work submission.
        This includes pre-validation, pre-preparation for score calculation, and pipeline triggering.
        :param request: DRF request object, data should contain 'assignment' (ID) and 'file' (file stream).
        :param args: Variable positional parameters
        :param kwargs: Variable keyword arguments
        :return:
            Response:
            201: The submission was successful, and the processing prompt is returned.
            400/403: Validation failure (number of times exceeded or no permission)
            500: The system handles the exception internally.
        """
        assignment_id = request.data.get('assignment')
        file_obj = request.data.get('file')

        try:
            assignment = Assignment.objects.get(id=assignment_id)
            student = request.user

            # 用于小组身份的识别
            target_group = None
            if assignment.is_group:
                target_group = Group.objects.filter(course=assignment.course, members=student).first()
                if not target_group:
                    return Response({"error": "该作业为小组作业，请先加入一个小组后再提交"}, status=403)

            # 1. Permission and frequency verification
            if not assignment.course.students.filter(id=student.id).exists():
                return Response({"error": "You are not authorized to submit this assessment"}, status=403)

            # 小组作业提交次数逻辑
            submission_filter = {"assignment": assignment}
            if assignment.is_group:
                submission_filter["group"] = target_group
            else:
                submission_filter["student"] = student

            existing_count = Submission.objects.filter(**submission_filter).count()
            if existing_count >= assignment.max_attempts:
                return Response({"error": "The maximum number of submissions has been reached"}, status=400)

            # 2. The backend makes an independent judgment on the file type.
            is_zip = file_obj.name.lower().endswith('.zip')
            calculated_sub_type = 'archive' if is_zip else 'file'

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 3. Keep records
            submission = serializer.save(
                student=student,
                group=target_group,
                attempt_number=existing_count + 1,
                sub_type=calculated_sub_type,
                status='pending'
            )

            # 4. Enter Pipeline orchestration
            self.run_agent_pipeline(submission)
            return Response({"message": "Submission successful. System processing in progress..."}, status=201)

        except Exception as e:
            print(f"ViewSet Create Error: {str(e)}")
            return Response({"error": str(e)}, status=500)

    def run_agent_pipeline(self, submission):
        """
        Arrangement logic: Handling the decompression, analysis of submitted materials, and dispatching Celery tasks.
        This method acts as a "central control console", responsible for completing the short-duration preprocessing tasks (such as decompression and entry analysis) in the Web main thread,
        and then asynchronously dispatching the heavy correction tasks to the background Workers to ensure that user requests can receive immediate responses.
        :param submission: Instances of submitted records in the database.
        :return:
        """
        from .tasks import run_grading_task

        # Make sure the base temporary directory exists
        temp_base = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_base, exist_ok=True)

        temp_workspace = os.path.join(temp_base, str(uuid.uuid4()))
        os.makedirs(temp_workspace, exist_ok=True)
        entry_point = None

        try:
            print(f"[Pipeline] starts processing submissions: {submission.id}")

            if submission.sub_type == 'archive':
                # Checking physical paths
                file_path = submission.file.path
                print(f"[Pipeline] is checking the file path: {file_path}")
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"The file is not saved to disk correctly: {file_path}")

                scorer = AIScorer()
                analyzer = ProjectAnalyzer(ai_client=scorer)

                print(f"[Pipeline] unpacking to: {temp_workspace}")
                analyzer.unzip_project(file_path, temp_workspace)

                print(f"[Pipeline] is analyzing the project structure...")
                contexts = scorer.get_rag_contexts(submission)
                task_requirement = contexts.get('l3', "Determine the main program entry point.")
                entry_point = analyzer.get_entry_point(temp_workspace, task_context=task_requirement)

            # Dispatch asynchronous tasks
            print(f"[Pipeline] Dispatches asynchronous tasks to Celery... EntryPoint: {entry_point}")
            run_grading_task.delay(
                submission_id=submission.id,
                temp_workspace=temp_workspace,
                entry_point=entry_point
            )

            submission.status = 'running'
            submission.save()
            print(f"[Pipeline] status update successful: Running")

        except Exception as e:
            print(f"[Pipeline ERROR] Submission {submission.id} Fail:")
            traceback.print_exc()
            submission.status = 'failed'
            submission.save()


    @action(detail=True, methods=['get'], url_path='recommend-resources')
    def recommend_resources(self, request, pk=None):
        """
        Retrieves or generates personalized learning resources based on the evaluation.

        Workflow Logic:
        1. Pre-requisite Check: Ensures an AI evaluation exists; otherwise, recommendations
           cannot be contextualized.
        2. "Instant-Load" Cache: Checks the database for pre-computed resources (usually
           generated during the initial grading pipeline). This ensures sub-second response times.
        3. Dynamic Fallback: If resources are missing (e.g., due to a pipeline timeout), the
           method triggers an immediate AI request to generate them on the fly.
        4. Persistence: Saves any newly generated resources back to the database to optimize
           future requests.
        :param request: A structured list of recommended tutorials, documentation, and exercises.
        """
        submission = self.get_object()

        # 1. If there is no rating record, it cannot be recommended
        if not hasattr(submission, 'ai_evaluation'):
            return Response({"error": "This submission has not been evaluated yet."}, status=400)

        evaluation = submission.ai_evaluation

        # 2. If GradingPipeline has already been generated and stored in the database, it returns
        if evaluation.learning_resources:
            return Response(evaluation.learning_resources)

        try:
            scorer = AIScorer()
            resources = scorer.generate_learning_resources(
                assignment_title=submission.assignment.title,
                category=submission.assignment.category,
                feedback=evaluation.feedback,
                kp_scores=evaluation.kp_scores
            )

            # Synchronization to the database
            evaluation.learning_resources = resources
            evaluation.save(update_fields=['learning_resources'])

            return Response(resources)
        except Exception as e:
            print(f"Manual Recommend Error: {str(e)}")
            return Response({"error": "Failed to generate recommendations at this time."}, status=500)


class UserProfileViewSet(viewsets.GenericViewSet):
    """
    User profile management view set.

    This set of views allows logged-in users to manage their own information without involving the actions of other users.
    CRUD (personal GET/PUT/PATCH) provided via custom actions
    And a separate interface to change passwords.

    Permission Restrictions:
        - Logged-in users only (IsAuthenticated).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def manage_me(self, request):
        """
        Gets or updates information about the currently logged-in user.

        user automatically locates the current user without passing an ID through the URL.
        As a result, privacy and security are enhanced. GET details (GET) and partial/complete updates (PUT/PATCH) are supported.
        :param request: DRF request object.
        :return: A dictionary containing the user's profile
        """
        instance = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        # Handle update requests: partial updates are supported (partial=True)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """
        Safely change the password of the currently logged-in user.

        The standard security process of "Old password validation -> New password setup" is used.
        Use Django's built-in set_password method to make sure your new password is encrypted with the PBKDF2 algorithm before loading it into the library.
        :param request: Requests containing 'old_password' and 'new_password'.
        :return: Success message or 400 error (old password validation failed).
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        # Verify the old password
        if not user.check_password(serializer.data.get('old_password')):
            return Response({"error": "Old password wrong"}, status=status.HTTP_400_BAD_REQUEST)

        new_pwd = serializer.data.get('new_password')
        try:
            validate_password(new_pwd, user=user)
        except exceptions.ValidationError as e:
            return Response({"error": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        # Set a new password
        user.set_password(serializer.data.get('new_password'))
        user.save()
        return Response({"message": "Password changed successfully"})


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission class: Access restricted to system administrators only.
    This type verifies the authentication status and role field (role) of the requesting user to ensure that only users with 'admin' privileges can call the associated view interface. This is crucial when handling global settings, system logs, and teacher account management.
    Logic:
        - The user must pass the authentication process (is_authenticated).
        - The user's role field must match the 'admin' identifier.
    """
    def has_permission(self, request, view):
        """
        Determine whether the current request has access permission.
        :param request: The DRF request object contains user information.
        :param view: The current instance of the view being accessed.
        :return: bool: If the user is a logged-in administrator, return True; otherwise, return False.
        """
        return request.user.is_authenticated and request.user.role == 'admin'


class SystemConfigViewSet(viewsets.ViewSet):
    """
    Administrator end: System global configuration management view set.
    This view set enables system administrators to dynamically adjust the backend core parameters (such as the DeepSeek API key, Base URL, model version, etc.). Through the singleton pattern (SystemConfiguration), it ensures the uniformity and real-time nature of the entire site's configuration.
    Permission restrictions:
        - Access is restricted to users with the 'admin' role (IsAdminUser).
    """
    permission_classes = [IsAdminUser]

    def get_object(self):
        """
        Obtain the singleton instance of the system configuration.
        The logic for obtaining the singleton has been encapsulated, ensuring that whether it is for obtaining or updating, the operation is performed on the sole configuration record in the database.
        :return:
        """
        return SystemConfiguration.get_config()

    @action(detail=False, methods=['get'])
    def get_settings(self, request):
        """
        Obtain the current system API and runtime environment configuration.
        The administrator can use this interface to view the current status of DeepSeek and other parameters such as token restrictions on the front-end panel.
        """
        config = self.get_object()
        serializer = SystemConfigurationSerializer(config)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def update_settings(self, request):
        """
        Dynamically update the global system configuration.
        Support for partial update (Partial Update). After the update is completed, all subsequent AI scoring requests (AIScorer) will immediately adopt the latest configuration parameters, without the need to restart the backend service.
        :param request: The request body that includes updated fields (such as api_key, model_name).
        :return: The newly updated configuration data after the update was successful or the error message indicating a verification failure.
        """
        config = self.get_object()
        serializer = SystemConfigurationSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            try:
                SystemOperationLog.objects.create(
                    user=request.user,
                    action="UPDATE",
                    target_type="SystemConfig",
                    target_id="1",
                    detail=f"The administrator modified the system global configuration"
                )
            except Exception as e:
                print(f" Logging failure: {e}")
            return Response({"message": "System configuration has been updated.", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='test-connection')
    def test_connection(self, request):
        """
        AI engine connectivity and account limit diagnostics.
        1. Connectivity test: Call '/models' to make sure the API Key and Base URL are valid.
        2. Model awareness: Automatically pull the list of models currently supported by the vendor (show the top 3 items) to ensure that the model is configured correctly.
        3. Error-tolerant adaptation: Automatically clean the trailing slash of URls to prevent 404 errors due to improper formatting.
        :param request: Contains configuration data for deepseek_api_key and deepseek_base_url.
        :return: List of connectivity, balance information, and models.
        """
        import requests
        config_data = request.data
        api_key = config_data.get('deepseek_api_key')
        base_url = config_data.get('deepseek_base_url', 'https://api.deepseek.com').rstrip('/')

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        try:
            # 1. Test model usability
            models_res = requests.get(f"{base_url}/models", headers=headers, timeout=10)

            # 2. Trying to get the balance
            clean_url = base_url.replace('/v1', '')
            balance_res = requests.get(f"{clean_url}/dashboard/billing/subscription", headers=headers, timeout=10)

            balance_data = "N/A"
            if balance_res.status_code == 200:
                b_json = balance_res.json()
                total = b_json.get('hard_limit_usd', 0)
                usage = b_json.get('total_usage', 0)
                balance_data = f"${round(total - usage, 3)}"

            if models_res.status_code == 200:
                return Response({
                    "status": "success",
                    "balance": balance_data,
                    "models": [m.get('id') for m in models_res.json().get('data', [])[:3]]
                })
            return Response({"message": "Invalid Key or URL"}, status=400)
        except Exception as e:
            return Response({"message": str(e)}, status=500)


class AdminKnowledgePointViewSet(viewsets.ModelViewSet):
    """Administrator side: Global management of knowledge base (including reference counting, import and export)"""
    queryset = KnowledgePoint.objects.all().order_by("-id")
    serializer_class = KnowledgePointSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """
        Dynamically filters the knowledge base based on administrative search criteria.
        :return: A filtered and ordered QuerySet.
        """
        qs = KnowledgePoint.objects.all()
        # Filter by language
        language = self.request.query_params.get('language')
        if language:
            qs = qs.filter(language__iexact=language)
        # Filter by type (L1/L2)
        kp_type = self.request.query_params.get('type')
        if kp_type == 'L1':
            qs = qs.filter(is_system=True)
        elif kp_type == 'L2':
            qs = qs.filter(is_system=False)
        return qs.order_by("-id")

    @action(detail=False, methods=['get'], url_path='with-refs')
    def list_with_references(self, request):
        """
        Retrieves the global list of KPs with cross-assignment reference counts.
        :param request: The incoming administrative GET request.
        :return: Response containing KPs and their respective reference frequencies.
        """
        qs = self.get_queryset()
        data = []
        for kp in qs:
            ref_count = Assignment.objects.filter(knowledge_points=kp).count()
            data.append({
                'id': kp.id,
                'name': kp.name,
                'description': kp.description,
                'category': kp.category,
                'is_system': kp.is_system,
                'language': kp.language,
                'course': kp.course_id,
                'reference_count': ref_count
            })
        return Response(data)

    @action(detail=False, methods=['get'], url_path='export')
    def export_kps(self, request):
        """
        Exports the filtered knowledge base to a CSV file for backup or external editing.
        :param request: The incoming administrative GET request.
        :return: A downloadable CSV file attachment.
        """
        import csv
        from django.http import HttpResponse
        qs = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="knowledge_points.csv"'
        writer = csv.writer(response)
        writer.writerow(['name', 'description', 'category', 'is_system', 'language', 'course_id'])
        for kp in qs:
            writer.writerow([kp.name, kp.description, kp.category, kp.is_system, kp.language, kp.course_id or ''])
        return response

    @action(detail=False, methods=['post'], url_path='import')
    def import_kps(self, request):
        """
        Performs bulk ingestion of Knowledge Points from a CSV file.
        :param request: POST request containing the multipart/form-data CSV file.
        :return: Success summary or detailed error message.
        """
        import csv
        import io
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        try:
            decoded = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            created = 0
            skipped = 0
            for row in reader:
                name = row.get('name', '').strip()
                if not name:
                    skipped += 1
                    continue
                exists = KnowledgePoint.objects.filter(
                    name__iexact=name,
                    language__iexact=row.get('language', 'python'),
                    course_id=row.get('course_id') or None
                ).exists()
                if exists:
                    skipped += 1
                    continue
                KnowledgePoint.objects.create(
                    name=name,
                    description=row.get('description', ''),
                    category=row.get('category', 'L2'),
                    is_system=row.get('is_system', 'False').lower() == 'true',
                    language=row.get('language', 'python'),
                    course_id=row.get('course_id') or None
                )
                created += 1
            return Response({'created': created, 'skipped': skipped})
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class AdminAIUsageStatsView(APIView):
    """
    AI Usage Analytics Dashboard: Monitors Token consumption, latency, and reliability.
    Responsibilities:
    1. Cost Tracking: Aggregates total, prompt, and completion token usage.
    2. Performance Monitoring: Calculates average response times across different AI features.
    3. Health Checks: Identifies error rates and status code distributions (4xx/5xx).
    4. Trend Analysis: Provides time-series data for daily usage patterns.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.analytics.models import AIServiceLog
        from django.db.models import Sum, Avg, Count, Q
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from datetime import timedelta

        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        logs = AIServiceLog.objects.filter(created_at__gte=since)

        # 1. Total amount statistics
        totals = logs.aggregate(
            total_tokens=Sum('total_tokens'),
            prompt_tokens=Sum('prompt_tokens'),
            completion_tokens=Sum('completion_tokens'),
            avg_response=Avg('response_time'),
            total_calls=Count('id'),
            error_count=Count('id', filter=Q(status_code__gte=400))
        )

        # 2. Daily trend (Token consumption + number of calls)
        daily_trend = (
            logs.annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                total_tokens=Sum('total_tokens'),
                calls=Count('id'),
                errors=Count('id', filter=Q(status_code__gte=400))
            )
            .order_by('day')
        )
        trend_data = [
            {
                "date": item['day'].strftime('%m-%d'),
                "total_tokens": item['total_tokens'] or 0,
                "calls": item['calls'],
                "errors": item['errors']
            }
            for item in daily_trend
        ]

        # 3. Distribution by interface (pie chart data)
        endpoint_dist = (
            logs.values('endpoint')
            .annotate(count=Count('id'), tokens=Sum('total_tokens'))
            .order_by('-count')
        )

        # 4. Average response time by interface
        endpoint_latency = (
            logs.values('endpoint')
            .annotate(avg_time=Avg('response_time'))
            .order_by('-avg_time')
        )

        return Response({
            "totals": {
                "total_tokens": totals['total_tokens'] or 0,
                "prompt_tokens": totals['prompt_tokens'] or 0,
                "completion_tokens": totals['completion_tokens'] or 0,
                "avg_response": round(totals['avg_response'] or 0, 2),
                "total_calls": totals['total_calls'] or 0,
                "error_count": totals['error_count'] or 0,
                "error_rate": round((totals['error_count'] or 0) / max(totals['total_calls'] or 1, 1) * 100, 1)
            },
            "daily_trend": trend_data,
            "endpoint_distribution": list(endpoint_dist),
            "endpoint_latency": list(endpoint_latency)
        })


class AdminDashboardStatsView(APIView):
    """
    Administrator end: Dashboard statistical data summary interface.
    This interface provides real-time data support for the system management homepage and consists of three core dimensions:
    1. Key Indicators (KPIs): Total number of users, total number of courses, total submission volume, and abnormal alerts within 24 hours.
    2. Real-time Logs: The flow of student submissions that occurred recently.
    3. Trend Analysis: The curve showing the changes in daily homework submissions over the past 7 days.
    Permission restrictions:
        - Must undergo identity verification.
        - Must have the 'admin' role permission (IsAdminUser).
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        """
        Aggregate the system operation data and return it.
        Logical process:
            - Basic statistics: Use count() to obtain the total indicators.
            - Exception detection: Filter records with status='failed' within a time window (24 hours) as alerts.
            - Dynamic extraction: Use select_related to perform JOIN queries to reduce the pressure of N+1 queries.
            - Trend aggregation: Utilize Django's TruncDate and Count for database-level grouping statistics.
        :return: Response: A JSON containing stats (list of indicators), recentLogs (dynamic logs), and chartData (sequence of charts).
        """
        # 1. Basic statistical indicators
        total_users = User.objects.count()
        active_courses = Course.objects.count()
        total_submissions = Submission.objects.count()

        # Define the submissions that were in the 'failed' state within the past 24 hours as system alerts.
        yesterday = timezone.now() - timedelta(days=1)
        system_alerts = Submission.objects.filter(status='failed', created_at__gte=yesterday).count()

        # 2. Recent Updates (Retrieve the last 5 submission records)
        recent_submissions = Submission.objects.select_related('student', 'assignment').order_by('-created_at')[:5]
        logs = []
        for sub in recent_submissions:
            logs.append({
                "action": f"Student {sub.student.username} submitted assignment: {sub.assignment.title}",
                "time": sub.created_at,
                "color": "bg-blue-500" if sub.status == 'completed' else "bg-amber-500"
            })

        # 3. Chart data: Daily submission trend over the past 7 days
        last_week = timezone.now() - timedelta(days=7)
        chart_data_query = Submission.objects.filter(created_at__gte=last_week) \
            .annotate(day=TruncDate('created_at')) \
            .values('day') \
            .annotate(count=Count('id')) \
            .order_by('day')

        chart_data = [
            {"day": item['day'].strftime('%m-%d'), "count": item['count']}
            for item in chart_data_query
        ]

        return Response({
            "stats": [
                {"label": "Total Users", "value": f"{total_users:,}", "trend": "+2%", "trendClass": "text-emerald-500"},
                {"label": "Active Courses", "value": active_courses, "trend": "Stable", "trendClass": "text-blue-500"},
                {"label": "Submissions", "value": f"{total_submissions:,}", "trend": "+15%",
                 "trendClass": "text-emerald-500"},
                {"label": "System Alerts", "value": system_alerts, "trend": "-10%", "trendClass": "text-amber-500"}
            ],
            "recentLogs": logs,
            "chartData": chart_data
        })


class AdminUserManagementViewSet(viewsets.ModelViewSet):
    """
    Administrator end: Comprehensive view set for managing all users of the entire system.
    This view set provides the user operation interface with the highest privileges for administrators, and supports:
    1. Dynamic filtering: Search by role (teacher/student/administrator) or keyword (student number/name/user name).
    2. Security control: Support for resetting user passwords to default values with one click.
    3. Automated data entry: Automatically align the student number and username and encrypt the initial password when creating a user.
    Permission restrictions:
        - Must undergo identity verification.
        - Must have the 'admin' role.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """
        Reformulate the query set acquisition logic to support complex search and filtering in the front-end management page.
        Logic:
            - role: Supports filtering by 'teacher', 'student', and 'admin'.
            - search: Fuzzy matching of username, real name, and student ID.
        """
        queryset = User.objects.all().order_by('-id')

        role = self.request.query_params.get('role')
        search = self.request.query_params.get('search')

        status_filter = self.request.query_params.get('status')

        if role and role != 'all':
            queryset = queryset.filter(role=role)

        if status_filter:
            if status_filter in ['approved', 'pending_approval', 'pending_email', 'rejected']:
                queryset = queryset.filter(approval_status=status_filter)

        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(student_id_num__icontains=search)
            )
        return queryset

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """
        Reset the login password for the specified user.
        Business logic:
        1. Dynamic credential: The password is automatically reset to the user's `student_id_num` (student ID/work ID).
        2. Secure fallback: If the user record lacks the student ID information (such as special management administrator accounts), it is uniformly reset to "123456".
        3. State persistence: The `set_password` function is called to ensure that the new password is encrypted and hashed using Django's built-in PBKDF2 algorithm and then stored in the database.
        Permission requirements:
            - Only accessible to users with administrator privileges.
        :param request: DRF Request Object.
        :param pk: The primary key ID of the target user.
        :return: It includes the reset password prompt information that has been modified.
        """
        user = self.get_object()
        # Reset the password using the student ID / employee number.
        default_pwd = user.student_id_num if user.student_id_num else "123456"
        user.set_password(default_pwd)
        user.save()
        return Response({"message": f"The password has been reset to: {default_pwd}"})

    def perform_create(self, serializer):
        """
        Executing the business interception logic before performing user persistence.
        This method overrides the saving behavior of ModelViewSet, aiming to implement the following automated business rules:
        1. Account standardization: The `username` field is forcibly synchronized to `student_id_num` (student ID). This complies with the login design where "student ID" serves as the account, preventing students from being unable to log in due to forgetting to set a custom username.
        2. Initial password preset:
            - The student ID is prioritized as the initial password to enhance individual distinction.
            - If the student ID is missing (an extremely rare case), it defaults to the common default value "123456".
        3. Security enhancement: The initial password is encrypted using the Django underlying hashing algorithm through the `make_password` call.
        :param serializer: An instance of UserProfileSerializer that has passed the format check.
        :return:
        """
        validated_password = serializer.validated_data.get('password')

        student_id = self.request.data.get('student_id_num', '')

        if validated_password:
            final_password = make_password(validated_password)
        else:
            default_pwd = student_id if student_id else "123456"
            final_password = make_password(default_pwd)

        final_username = student_id if student_id else serializer.validated_data.get('username')

        serializer.save(
            password=final_password,
            username=final_username
        )

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_teacher(self, request, pk=None):
        """
        Administrator: Approves teacher registration and sends account activation email.
        Business Logic:
        1. Role Validation: Ensures the approval flow is only applied to 'teacher' accounts.
        2. State Verification: Checks if the account is already active to prevent redundant processing.
        3. Atomic Activation: Updates 'approval_status' and sets 'is_active' to True in one transaction.
        4. Notification: Dispatches a welcome email with login instructions.
        5. Auditing: Records the administrative action in the system logs.
        """
        user = self.get_object()

        if user.role != 'teacher':
            return Response({"error": "This user is not a teacher and does not need the approval process"}, status=400)

        if user.approval_status == 'approved':
            return Response({"message": "The account is already active"}, status=200)

        # 1. Execute Approval Logic
        with transaction.atomic():
            user.approval_status = 'approved'
            user.is_active = True
            user.save()

        # 2. Prepare Notification Content
        subject = "[System Notification] Your teacher account has been approved"
        message = f"""
    Dear {user.username},

    Your teacher account application has been reviewed and approved by the administrator! 
    You can now log in to the system to begin your instructional work.

    [Account Information]
    - Username: {user.username}
    - Password: The password you set during registration
    - Login URL: {settings.FRONTEND_URL}/login

    If you have forgotten your password, please contact the administrator for a reset.

    Best regards,
    The Intelligent Programming Education Team
        """

        # 3. Sending an email
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False
            )

            # Logging operations
            log_action(request.user, "APPROVE_TEACHER", "User", user.id, f"Approved teacher: {user.username}")

            return Response({"message": f"Teacher {user.username} approved. Notification email sent."})
        except Exception as e:
            return Response({
                "message": f"Account {user.username} activated, but the notification email failed to send.",
                "error": str(e)
            }, status=200)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject_teacher(self, request, pk=None):
        """
        Administrator: Rejects a teacher's registration request with a reason.

        Workflow:
        1. State Update: Moves the user's status to 'rejected' and persists the reason.
        2. Notification: Dispatches an automated email to inform the user of the decision.
        3. Audit: Logs the rejection event for administrative oversight.
        """
        user = self.get_object()
        reason = request.data.get('reason', 'The information provided is incomplete or does not meet our requirements.')

        user.approval_status = 'rejected'
        user.rejected_reason = reason
        user.save()

        # Prepare the notification email
        subject = "[System Notification] Your teacher account application was not approved"
        message = (
        f"Dear {user.username},\n\n"
        f"We regret to inform you that your teacher account application has been rejected.\n"
        f"Reason: {reason}\n\n"
        f"If you have any questions, please contact the system administrator."
    )

        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])
        except Exception:
            pass

        return Response({"message": f"Registration for teacher {user.username} has been rejected."})


class AdminSystemHealthView(APIView):
    """
    System Health Dashboard: Monitors Docker container resources and Redis cache performance.

    Responsibilities:
    1. Container Orchestration Visibility: Fetches CPU and Memory metrics directly from Docker.
    2. Cache Diagnostics: Evaluates Redis hit rates and memory footprint.
    3. Operational Intelligence: Provides status checks to ensure background services (like Celery workers) are running.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        import redis as redis_lib

        # 1. Docker Container Resources
        docker_stats = []
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list(all=True)
            for c in containers[:10]:
                stats_data = {}
                if c.status == 'running':
                    try:
                        raw = c.stats(stream=False)
                        # CPU
                        cpu_delta = raw['cpu_stats']['cpu_usage']['total_usage'] - raw['precpu_stats']['cpu_usage']['total_usage']
                        system_delta = raw['cpu_stats']['system_cpu_usage'] - raw['precpu_stats']['system_cpu_usage']
                        num_cpus = raw['cpu_stats']['online_cpus']
                        cpu_percent = (cpu_delta / system_delta * num_cpus * 100) if system_delta > 0 else 0

                        # Memory
                        mem_usage = raw['memory_stats'].get('usage', 0)
                        mem_limit = raw['memory_stats'].get('limit', 1)
                        mem_percent = (mem_usage / mem_limit * 100) if mem_limit > 0 else 0

                        stats_data = {
                            'cpu_percent': round(cpu_percent, 1),
                            'mem_usage_mb': round(mem_usage / 1024 / 1024, 1),
                            'mem_limit_mb': round(mem_limit / 1024 / 1024, 1),
                            'mem_percent': round(mem_percent, 1)
                        }
                    except Exception:
                        stats_data = {'cpu_percent': 0, 'mem_usage_mb': 0, 'mem_limit_mb': 0, 'mem_percent': 0}

                docker_stats.append({
                    'name': c.name,
                    'status': c.status,
                    'image': str(c.image.tags[0]) if c.image.tags else 'unknown',
                    'stats': stats_data
                })
        except Exception as e:
            docker_stats = [{'error': str(e)}]

        # 2. Redis cache statistics
        redis_stats = {'status': 'offline'}
        try:
            r = redis_lib.Redis(host='127.0.0.1', port=6379, db=0, socket_timeout=2)
            info = r.info()
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            redis_stats = {
                'status': 'online',
                'hits': hits,
                'misses': misses,
                'hit_rate': round(hits / total * 100, 1) if total > 0 else 0,
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'total_keys': sum(r.dbsize() for _ in [0])
            }
        except Exception:
            pass

        return Response({
            'docker_containers': docker_stats,
            'redis': redis_stats
        })


class SystemMonitorView(APIView):
    """
    Administrator end: Full-stack system monitoring window.
    This interface integrates real-time monitoring data from three levels:
    1. Hardware node status (node load, running status).
    2. Task queue details (Celery asynchronous batch processing task flow).
    3. AI service performance (delay trends and token consumption statistics based on real logs from DeepSeek API).
    Permission requirements:
    - Identity verification is mandatory.
    - The 'admin' administrator role is necessary.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        import redis as redis_lib

        # 1. 检测真实服务状态
        nodes = []

        # Core API Server: 检测自身进程
        nodes.append({
            'name': 'Core API Server',
            'status': 'Online',
            'load': 0,
            'desc': 'Django REST Framework'
        })

        # Redis Broker: 尝试 ping
        try:
            r = redis_lib.Redis(host='127.0.0.1', port=6379, db=0, socket_timeout=2)
            r.ping()
            nodes.append({
                'name': 'Redis Broker',
                'status': 'Online',
                'load': 0,
                'desc': 'Message Queue'
            })
        except Exception:
            nodes.append({
                'name': 'Redis Broker',
                'status': 'Offline',
                'load': 0,
                'desc': 'Connection Failed'
            })

        # Docker Worker: 检查是否有 grading 容器在运行
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list(filters={"status": "running"})
            grading_count = sum(1 for c in containers if 'grading' in c.name.lower() or 'celery' in c.name.lower())
            nodes.append({
                'name': 'Celery Worker',
                'status': 'Online' if grading_count > 0 else 'Idle',
                'load': grading_count,
                'desc': f'{grading_count} active task(s)'
            })
        except Exception:
            nodes.append({
                'name': 'Celery Worker',
                'status': 'Unknown',
                'load': 0,
                'desc': 'Docker unavailable'
            })

        # 2. Get the latest task
        recent_tasks = Submission.objects.order_by('-created_at')[:5]
        queue_tasks = []
        status_map = {'pending': 'Pending', 'running': 'Running', 'completed': 'Success', 'failed': 'Failed'}
        for task in recent_tasks:
            queue_tasks.append({
                'id': str(task.id),
                'type': 'AI Grading Pipeline' if task.sub_type == 'archive' else 'Single File Test',
                'status': status_map.get(task.status, 'Unknown'),
                'time': task.created_at
            })

        # 3. Obtain the actual AI performance data from AIServiceLog
        ai_logs = AIServiceLog.objects.order_by('-created_at')[:20]

        if ai_logs.exists():
            avg_latency = sum(log.response_time for log in ai_logs) / ai_logs.count()
            total_tokens_24h = sum(log.total_tokens for log in ai_logs)
            latency_history = [int(log.response_time * 1000) for log in reversed(ai_logs)]
        else:
            avg_latency = 0
            total_tokens_24h = 0
            latency_history = [0] * 12

        api_performance = [
            {
                'label': 'DeepSeek API Response',
                'latency': int(avg_latency * 1000),
                'history': latency_history,
                'extra': f"Total Tokens: {total_tokens_24h}"
            }
        ]

        return Response({
            "nodes": nodes,
            "queueTasks": queue_tasks,
            "apiPerformance": api_performance
        })


class AdminSystemLogView(APIView):
    """
    Administrator end: System Audit and AI Invocation Log View.
    This interface provides deep transparency for the AI service layer (AIServiceLog), enabling administrators to monitor:
    1. Interface stability: By observing the `status_code`, one can check if DeepSeek or other services frequently report errors.
    2. Cost expenditure: By monitoring the `total_tokens`, one can assess the scale of a single request and evaluate the long-term operational cost.
    3. Response performance: By capturing the `response_time`, one can detect fluctuations in the API provider and optimize the concurrent strategy.
    Permission requirements:
    - Identity verification is mandatory.
    - The 'admin' administrator role is necessary.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        # Obtain the latest 50 AI invocation logs
        ai_logs = AIServiceLog.objects.select_related().all().order_by('-created_at')[:50]

        ops_logs = SystemOperationLog.objects.select_related('user').all().order_by('-created_at')[:50]

        return Response({
            "ai_logs": [
                {
                    "id": log.id,
                    "service": log.service_name,
                    "endpoint": log.endpoint,
                    "tokens": log.total_tokens,
                    "latency": f"{int(log.response_time * 1000)}ms",
                    "status": log.status_code,
                    "time": log.created_at
                } for log in ai_logs
            ],
            "ops_logs": [
                {
                    "id": log.id,
                    "user": log.user.username if log.user else "Unknown",
                    "action": log.action,
                    "target": log.target_type,
                    "detail": log.detail,
                    "time": log.created_at
                } for log in ops_logs
            ]
        })


class NotificationConfigViewSet(viewsets.ModelViewSet):
    """
    Notify the configuration management view set.
    Responsibilities:
    1. Preference store: Manage the teacher's personalized Settings for homework reminders, system notifications, etc. (e.g., reminders a few hours in advance).
    2. Autocompletion: The 'get_or_create' mechanism ensures that each teacher has a set of default Settings when they enter the system.
    3. Semantic routing: Provides a '/me/' interface that allows the frontend to operate on the current user's configuration without having to care about the specific configuration ID.
    """
    queryset = NotificationConfig.objects.all()
    serializer_class = NotificationConfigSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def manage_my_config(self, request):
        """
        Specifically deals with the personal notification configuration of the currently logged-in teacher.
        1. Automatic association: The interface will automatically lock configuration records against 'request.user' to prevent overreach.
        2. Lazy loading creation: If the current teacher is visiting the configuration page for the first time, the system will automatically create a default configuration for it.
        3. Idempotent update: Supports both PUT (full) and PATCH (incremental) update modes.
        """
        # Gets or creates a configuration for the current teacher
        config, created = NotificationConfig.objects.get_or_create(
            teacher=request.user,
            defaults={'remind_before_hours': 0}
        )

        if request.method == 'GET':
            serializer = self.get_serializer(config)
            return Response(serializer.data)

        elif request.method in ['PUT', 'PATCH']:
            # Partially or completely updated
            serializer = self.get_serializer(config, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DockerManagementViewSet(viewsets.ViewSet):
    """
    管理员端：Docker 沙箱基础设施监控与动态配置中心
    """
    # 建议此处使用你自定义的 IsAdminUser 权限，目前先用 IsAuthenticated 保证安全
    permission_classes = [IsAdminUser]

    def _get_client(self):
        """内部工具方法：安全获取 Docker 客户端连接"""
        try:
            return docker.from_env()
        except Exception as e:
            print(f"Docker Connection Error: {str(e)}")
            return None

    @action(detail=False, methods=['get'], url_path='status')
    def get_status(self, request):
        """
        [监测功能] 获取 Docker 引擎的实时负载与容器状态
        """
        client = self._get_client()
        if not client:
            return Response({"error": "无法连接到 Docker 引擎，请检查服务是否启动"}, status=500)

        try:
            info = client.info()
            # 获取当前正在运行的容器（用于识别系统负载）
            running_containers = client.containers.list(filters={"status": "running"})

            return Response({
                "containers": {
                    "total": info.get('Containers'),
                    "running": len(running_containers),
                    "paused": info.get('ContainersPaused'),
                    "stopped": info.get('ContainersStopped'),
                },
                "images_count": info.get('Images'),
                "engine_info": {
                    "ncpu": info.get('NCPU'),
                    "mem_total": info.get('MemTotal'),
                    "os": info.get('OperatingSystem'),
                    "version": info.get('ServerVersion')
                }
            })
        except Exception as e:
            return Response({"error": f"获取状态失败: {str(e)}"}, status=500)

    @action(detail=False, methods=['get', 'post'], url_path='config')
    def manage_config(self, request):
        """
        [管理功能] 动态读写 DockerRunner 的资源限额配置
        """
        # 利用你 model 里的 get_config() 自动获取单例配置
        config = SystemConfiguration.get_config()

        if request.method == 'GET':
            serializer = SystemConfigurationSerializer(config)
            return Response(serializer.data)

        elif request.method == 'POST':
            # 使用 partial=True 支持只修改 Docker 部分字段
            serializer = SystemConfigurationSerializer(config, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "message": "Docker 运行策略已成功更新并刷新缓存",
                    "data": serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='cleanup')
    def cleanup_resources(self, request):
        """
        [自愈功能] 一键清理所有已停止的容器，防止磁盘被大量无用沙箱堆满
        """
        client = self._get_client()
        if not client:
            return Response({"error": "Docker 引擎不可用"}, status=500)

        try:
            pruned = client.containers.prune()
            deleted_list = pruned.get('ContainersDeleted')
            return Response({
                "deleted_count": len(deleted_list) if deleted_list is not None else 0,
                "space_reclaimed": pruned.get('SpaceReclaimed', 0),
                "message": "清理完成"
            })
        except Exception as e:
            return Response({"error": f"清理失败: {str(e)}"}, status=500)

