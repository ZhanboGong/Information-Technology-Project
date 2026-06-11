import json
import re
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from rest_framework import serializers
from .models import (User, Assignment, Submission, Course, AIEvaluation, KnowledgePoint, DockerReport,
                     SystemConfiguration, Appeal, NotificationConfig, Group, TeachingInsightReport, Announcement, AssignmentAttachment)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# --- 1. User serializer---
class UserSerializer(serializers.ModelSerializer):
    """
    Serialization of basic user information.
    It is used to show the personal profile of students or teachers and hide sensitive information.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'student_id_num', 'class_name', 'first_name']
        read_only_fields = ['id', 'role']


# --- 2. Login token serializer ---
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT authentication serializer.
    In addition to returning the Access/Refresh Token, it injects common contexts such as user role and username.
    Reduce the number of requests to the user information interface again after the front-end login.
    """
    def validate(self, attrs):
        """
        Rewrite the validation logic: While generating the Token, extract and return the user information.
        :param attrs: The original properties dictionary containing username and password.
        :return: A dictionary containing access, refresh, and extension information such as role and username.
        """
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['username'] = self.user.username
        data['user_id'] = self.user.id
        data['student_id'] = self.user.student_id_num
        return data


# --- 3. Knowledge point serializer ---
class KnowledgePointSerializer(serializers.ModelSerializer):
    """
    Knowledge point dictionary serializer.
    Used in the job detail page to convert the knowledge point ID into specific readable information.
    """
    class Meta:
        model = KnowledgePoint
        fields = ['id', 'name', 'category', 'is_system', 'language', 'bloom_level', 'description', 'course']


# --- 4. The course serializer ---
class CourseSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(source='students.count', read_only=True)
    teacher_name = serializers.ReadOnlyField(source='teacher.username')

    teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='teacher'),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'description', 'teacher', 'teacher_name',
            'student_count', 'created_at', 'invite_code'
        ]
        read_only_fields = ['id', 'created_at', 'invite_code']

    def __init__(self, *args, **kwargs):
        super(CourseSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')

        if request and request.user:
            if request.user.role != 'admin':
                self.fields['teacher'].read_only = True


class GroupSerializer(serializers.ModelSerializer):
    """
    暂时不用
    """
    member_details = UserSerializer(source='members', many=True, read_only=True)
    leader_name = serializers.ReadOnlyField(source='leader.username')
    course_name = serializers.ReadOnlyField(source='course.name')

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'course', 'course_name', 'leader',
            'leader_name', 'members', 'member_details',
            'invite_code', 'created_at'
        ]
        read_only_fields = ['id', 'leader', 'invite_code', 'created_at']


class AssignmentAttachmentSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField()
    assignment = serializers.PrimaryKeyRelatedField(queryset=Assignment.objects.all())

    class Meta:
        model = AssignmentAttachment
        fields = ['id', 'assignment', 'file', 'filename', 'uploaded_at']
        read_only_fields = ['uploaded_at']

    def get_filename(self, obj):
        return obj.filename()


# --- 5. Assessment serializer ---
class AssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Assignment model.

    Responsibilities:
    1. Relation Mapping: Flattens related object data (e.g., Course Name).
    2. Computed Fields: Uses SerializerMethodFields to provide real-time stats like submission counts.
    3. UI Helpers: Extracts file names from attachment paths for better display.
    4. Knowledge Point Integration: Nested serialization for detailed KP insights.
    """
    course_name = serializers.ReadOnlyField(source='course.name')
    kp_details = KnowledgePointSerializer(source='knowledge_points', many=True, read_only=True)
    attachment_name = serializers.SerializerMethodField()

    has_report = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()
    reference_files = AssignmentAttachmentSerializer(many=True, read_only=True)


    class Meta:
        model = Assignment
        fields = [
            'id',
            'title',
            'course_name',
            'content',
            'course',
            'deadline',
            'rubric_config',
            'max_attempts',
            'reference_logic',
            'knowledge_points',
            'kp_details',
            'teacher',
            'category',
            'reference_files',
            'attachment',
            'attachment_name',
            'is_group',
            'max_group_size',
            'submission_count',
            'total_students',
            'created_at',
            'updated_at',
            'has_report'
        ]
        read_only_fields = ['teacher', 'created_at', 'updated_at']

    def get_attachment_name(self, obj):
        """
        Extracts the base filename from the attachment path.
        :param obj: The Assignment instance.
        :return: String filename or None.
        """
        if obj.attachment:
            import os
            return os.path.basename(obj.attachment.name)
        return None

    def get_has_report(self, obj):
        """
        Checks if a teaching insight report is ready for the teacher.
        :param obj: The Assignment instance.
        :return: Boolean flag for frontend conditional rendering.
        """
        try:
            return hasattr(obj, 'teaching_report') and obj.teaching_report.status == 'ready'
        except:
            return False

    def get_submission_count(self, obj):
        """
        Calculates the number of unique students who have completed this task.
        Logic: Filters for 'completed' status and counts distinct students
        to avoid over-counting multiple attempts.
        :param obj: The Assignment instance.
        :return: Integer count of successful participants.
        """
        from .models import Submission
        return Submission.objects.filter(assignment=obj, status='completed').values('student').distinct().count()

    def get_total_students(self, obj):
        return obj.course.students.count()


class TeachingInsightReportSerializer(serializers.ModelSerializer):
    """
    Serializer for the TeachingInsightReport model.
    """
    class Meta:
        model = TeachingInsightReport
        fields = ['status', 'generated_at', 'stats_data', 'ai_insights']
        read_only_fields = ['status', 'generated_at']


# --- 9. Appeal Serializer ---
class AppealSerializer(serializers.ModelSerializer):
    """
    Serializer for the Grade Appeal model.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    student_name = serializers.ReadOnlyField(source='evaluation.submission.student.username')
    student_id_num = serializers.ReadOnlyField(source='evaluation.submission.student.student_id_num')
    assignment_title = serializers.ReadOnlyField(source='evaluation.submission.assignment.title')
    original_score = serializers.ReadOnlyField(source='evaluation.total_score')

    teacher_id = serializers.ReadOnlyField(source='evaluation.submission.assignment.teacher.id')
    teacher_name = serializers.ReadOnlyField(source='evaluation.submission.assignment.teacher.username')

    class Meta:
        model = Appeal
        fields = [
            'id',
            'student_name',
            'student_id_num',
            'assignment_title',
            'original_score',
            'student_reason',
            'ai_judgment',
            'status',
            'status_display',
            'teacher_id',
            'teacher_name',
            'teacher_remark',
            'adjusted_score',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'ai_judgment', 'status', 'created_at', 'updated_at']


# --- 6. AI evaluation result serializer ---
class AIEvaluationSimpleSerializer(serializers.ModelSerializer):
    """

    """
    ai_raw_feedback_data = serializers.SerializerMethodField()
    appeal = AppealSerializer(read_only=True)

    class Meta:
        model = AIEvaluation
        fields = [
            'id',
            'total_score',
            'ai_raw_score',
            'feedback',
            'scores',
            'kp_scores',
            'learning_resources',
            'static_analysis',
            'is_published',
            'teacher_reviewed',
            'ai_raw_feedback',
            'ai_raw_feedback_data',
            'raw_sandbox_output',
            'appeal',
            'created_at'
        ]

    def get_ai_raw_feedback_data(self, obj):
        """

        :param obj:
        :return:
        """
        if not obj.ai_raw_feedback:
            return None
        try:
            return json.loads(obj.ai_raw_feedback)
        except (json.JSONDecodeError, TypeError):
            return obj.ai_raw_feedback


# --- 7. Docker Report Serializer ---
class DockerReportSerializer(serializers.ModelSerializer):
    """
    Sandbox runs the report serializer.
    Shows the raw state data of the underlying container after execution.
    """
    class Meta:
        model = DockerReport
        fields = ['exit_code', 'stdout', 'compile_status', 'execution_time', 'status']


# --- 8. Submission Serializer ---
class SubmissionSerializer(serializers.ModelSerializer):
    """
    Submission record core serializer (integrates highest score logic).
    This class is nested with multiple SerializerMethodFields,
    All the data requirements for "one request to get the submission and the associated highest score" are implemented.
    """
    assignment_info = AssignmentSerializer(source='assignment', read_only=True)

    ai_evaluation = AIEvaluationSimpleSerializer(read_only=True)

    docker_report = DockerReportSerializer(read_only=True)

    student_name = serializers.ReadOnlyField(source='student.username')

    ai_score = serializers.SerializerMethodField()

    has_appeal = serializers.SerializerMethodField()

    active_appeal_data = serializers.SerializerMethodField()

    group_name = serializers.ReadOnlyField(source='group.name')

    class Meta:
        model = Submission
        fields = [
            'id',
            'student',
            'student_name',
            'assignment',
            'group',
            'group_name',
            'assignment_info',
            'ai_evaluation',
            'docker_report',
            'file',
            'status',
            'sub_type',
            'final_score',
            'ai_score',
            'created_at',
            'has_appeal',
            'active_appeal_data',
            'attempt_number'
        ]
        read_only_fields = ['student', 'status', 'final_score', 'sub_type', 'attempt_number']

    def get_ai_score(self, obj):
        """
        Maintain logical consistency:
        If final_score was already computed and stored by GradingPipeline, it is returned.
        This ensures that the ai_score field displayed on the frontend is always the all-time high.
        :param obj: The Submission instance that is currently being serialized.
        :return: The final presentation score.
        """
        if obj.final_score is not None:
            return obj.final_score

        try:
            return obj.ai_evaluation.total_score
        except:
            return 0

    def get_has_appeal(self, obj):
        view = self.context.get('view')
        if not view or getattr(view, 'action', None) != 'retrieve':
            return False
        return Appeal.objects.filter(
            evaluation__submission__assignment=obj.assignment,
            evaluation__submission__student=obj.student
        ).exists()

    def get_active_appeal_data(self, obj):
        view = self.context.get('view')
        if not view or getattr(view, 'action', None) != 'retrieve':
            return None
        appeal = Appeal.objects.filter(
            evaluation__submission__assignment=obj.assignment,
            evaluation__submission__student=obj.student
        ).first()
        if appeal:
            return AppealSerializer(appeal).data
        return None


class UserProfileSerializer(serializers.ModelSerializer):
    """A general serializer used for administrators to manage users and for users to view their personal profiles"""
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'email',
            'role',
            'student_id_num',
            'is_active',
            'class_name',
            'enable_deadline_reminder',
            'date_joined',
            'approval_status',
            'rejected_reason',
            'password'
        ]

        read_only_fields = ['id', 'date_joined', 'approval_status', 'rejected_reason']

    def __init__(self, *args, **kwargs):
        super(UserProfileSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')

        if request and request.user and request.user.role != 'admin':
            self.fields['role'].read_only = True
            self.fields['student_id_num'].read_only = True
            self.fields['is_active'].read_only = True
            self.fields['username'].read_only = True

    def validate_password(self, value):
        try:
            validate_password(value)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Modify the password-specific serializer.

    This serializer is not directly associated with the database model and is only used to validate what the user submitted in the Change password interface
    The format and existence of old_password and new_password.

    Validation logic:
        -old_password: This is a required field used by the backend to validate the user's identity.
        -new_password: Required, new credentials the user wishes to set.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class SystemConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfiguration
        fields = ['id', 'deepseek_api_key', 'deepseek_base_url', 'deepseek_model_name',
                  'docker_mem_limit', 'docker_cpu_quota', 'docker_pids_limit', 'docker_timeout']
        read_only_fields = ['id']

    def validate_docker_mem_limit(self, value):
        """Verify memory limit format: 512m, 1g, 1024k"""
        if not re.match(r'^\d+[kmg]?$', str(value).lower()):
            raise serializers.ValidationError("内存限制格式无效。请使用数字加单位（如 '512m', '1g'）。")
        return value

    def validate_docker_cpu_quota(self, value):
        """Verify CPU quota: 0.1 core - 4 cores"""
        if value < 100000000:
            raise serializers.ValidationError("If the CPU quota is too low, the container may not start.")
        if value > 4000000000:
            raise serializers.ValidationError("CPU quota exceeds the system's preset safety limit (up to 4 cores).")
        return value

    def validate_docker_pids_limit(self, value):
        """Verify the maximum number of processes"""
        if value < 10 or value > 500:
            raise serializers.ValidationError("The maximum number of processes should be between 10 and 500.")
        return value

    def validate_docker_timeout(self, value):
        """Verify the timeout"""
        try:
            timeout_val = int(value)
            if timeout_val < 5 or timeout_val > 300:
                raise serializers.ValidationError("The timeout must be between 5 and 300 seconds.")
            return timeout_val
        except (ValueError, TypeError):
            raise serializers.ValidationError("The timeout must be a valid integer.")

    def validate_deepseek_api_key(self, value):
        """Verify API Key robustness"""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Invalid DeepSeek API Key.")
        return value


class NotificationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationConfig
        fields = ['enable_report', 'remind_before_hours', 'subject_template']
        read_only_fields = ['teacher']


class AnnouncementSerializer(serializers.ModelSerializer):
    teacher_name = serializers.ReadOnlyField(source='teacher.first_name')

    class Meta:
        model = Announcement
        fields = ['id', 'course', 'teacher', 'teacher_name', 'content', 'created_at']
        read_only_fields = ['teacher', 'created_at']




