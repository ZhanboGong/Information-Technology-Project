import json
from rest_framework import serializers
from .models import User, Assignment, Submission, Course, AIEvaluation, KnowledgePoint, DockerReport, SystemConfiguration
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
        fields = ['id', 'name', 'category', 'is_system', 'description']


# --- 4. The course serializer ---
class CourseSerializer(serializers.ModelSerializer):
    """
    Course data serializer.
    The reverse statistics function is integrated to show how active the course is.
    """
    student_count = serializers.IntegerField(source='students.count', read_only=True)
    teacher_name = serializers.ReadOnlyField(source='teacher.username')

    class Meta:
        model = Course
        fields = ['id', 'name', 'description', 'teacher', 'teacher_name', 'student_count', 'created_at']


# --- 5. Assessment serializer ---
class AssignmentSerializer(serializers.ModelSerializer):
    # 你声明了它
    course_name = serializers.ReadOnlyField(source='course.name')
    kp_details = KnowledgePointSerializer(source='knowledge_points', many=True, read_only=True)
    attachment_name = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        # 🚀 必须确保 course_name 出现在这个 fields 列表里！
        fields = [
            'id',
            'title',
            'course_name',  # <--- 检查并添加这一行
            'content',
            'course',
            'deadline',
            'rubric_config',
            'max_attempts',
            'reference_logic',
            'knowledge_points',
            'kp_details',   # <--- 顺便检查它是否也漏掉了
            'teacher',
            'category',
            'attachment',
            'attachment_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['teacher', 'created_at', 'updated_at']

    def get_attachment_name(self, obj):
        if obj.attachment:
            import os
            return os.path.basename(obj.attachment.name)
        return None


# --- 6. AI evaluation result serializer ---
class AIEvaluationSimpleSerializer(serializers.ModelSerializer):
    ai_raw_feedback_data = serializers.SerializerMethodField()

    class Meta:
        model = AIEvaluation
        fields = [
            'id',
            'total_score',
            'ai_raw_score',      # 建议加上：AI原始分
            'feedback',
            'scores',
            'kp_scores',
            'is_published',
            'teacher_reviewed',  # 建议加上：老师是否已审阅
            'ai_raw_feedback',
            'ai_raw_feedback_data',
            'raw_sandbox_output',
            'created_at'
        ]

    def get_ai_raw_feedback_data(self, obj):
        if not obj.ai_raw_feedback:
            return None
        try:
            # 尝试将 TextField 里的字符串转为 Python 对象发送
            # 这样前端直接拿到的就是 Object，不需要再 JSON.parse
            return json.loads(obj.ai_raw_feedback)
        except (json.JSONDecodeError, TypeError):
            # 如果不是标准的 JSON 格式（比如存的是纯提示文本），则返回原始文本
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

    class Meta:
        model = Submission
        fields = [
            'id',
            'student',
            'student_name',
            'assignment',
            'assignment_info',
            'ai_evaluation',
            'docker_report',
            'file',
            'status',
            'sub_type',
            'final_score',
            'ai_score',
            'created_at',
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


class UserProfileSerializer(serializers.ModelSerializer):
    """用于管理员管理用户和用户查看个人资料的通用序列化器"""

    class Meta:
        model = User
        # 包含模型中定义的所有关键字段
        fields = [
            'id',
            'username',
            'first_name',
            'email',
            'role',
            'student_id_num',
            'is_active',
            'class_name',
            'date_joined'
        ]

        # 将 username 设为只读，因为它是登录账号，通常不建议频繁修改
        # 如果你希望管理员能改 username，就把下面这行去掉
        read_only_fields = ['id', 'date_joined']

    def __init__(self, *args, **kwargs):
        # 动态处理权限：如果不是管理员，强制锁定关键字段
        super(UserProfileSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')

        if request and request.user and request.user.role != 'admin':
            # 普通用户不能修改 角色、学号、激活状态
            self.fields['role'].read_only = True
            self.fields['student_id_num'].read_only = True
            self.fields['is_active'].read_only = True
            self.fields['username'].read_only = True

class ChangePasswordSerializer(serializers.Serializer):
    """用于修改密码的序列化器"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class SystemConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfiguration
        fields = ['deepseek_api_key', 'deepseek_base_url', 'deepseek_model_name']