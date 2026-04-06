from rest_framework import serializers
from .models import User, Assignment, Submission, Course, AIEvaluation, KnowledgePoint, DockerReport
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
    """
    Assessment detail serializer.
    The nested design is used to completely package the job configuration information with the associated knowledge point metadata.
    """
    course_name = serializers.ReadOnlyField(source='course.name')
    kp_details = KnowledgePointSerializer(source='knowledge_points', many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'content', 'course', 'course_name',
            'deadline', 'rubric_config', 'max_attempts',
            'reference_logic', 'knowledge_points', 'kp_details',
            'category', 'created_at'
        ]


# --- 6. AI evaluation result serializer ---
class AIEvaluationSimpleSerializer(serializers.ModelSerializer):
    """
    Single-pass evaluation feedback serializer.
    Focus on showing specific rating facts and AI feedback for a particular submission.
    """
    class Meta:
        model = AIEvaluation
        # Note: total_score here is the score for a single commit
        fields = ['total_score', 'feedback', 'scores', 'kp_scores', 'raw_sandbox_output', 'is_published']


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
            'final_score',  # 🚀 重点：这里现在存的是“历史最高分”
            'ai_score',  # 🚀 重点：这里返回的是“历史最高分”
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