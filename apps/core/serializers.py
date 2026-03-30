from rest_framework import serializers
from .models import User, Assignment, Submission, Course, AIEvaluation, KnowledgePoint, DockerReport
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# --- 1. 用户序列化器 (保持原样) ---
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'student_id_num', 'class_name', 'first_name']
        read_only_fields = ['id', 'role']


# --- 2. 登录令牌序列化器 (保持原样) ---
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['username'] = self.user.username
        data['user_id'] = self.user.id
        data['student_id'] = self.user.student_id_num
        return data


# --- 3. 知识点序列化器 (保持原样) ---
class KnowledgePointSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgePoint
        fields = ['id', 'name', 'category', 'is_system', 'description']


# --- 4. 课程序列化器 (保持原样) ---
class CourseSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(source='students.count', read_only=True)
    teacher_name = serializers.ReadOnlyField(source='teacher.username')

    class Meta:
        model = Course
        fields = ['id', 'name', 'description', 'teacher', 'teacher_name', 'student_count', 'created_at']


# --- 5. 作业序列化器 (保持原样) ---
class AssignmentSerializer(serializers.ModelSerializer):
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


# --- 6. AI 评价结果简版 (代表“本次提交”的得分详情) ---
class AIEvaluationSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIEvaluation
        # 注意：这里的 total_score 是单次提交的得分
        fields = ['total_score', 'feedback', 'scores', 'kp_scores', 'raw_sandbox_output', 'is_published']


# --- 7. Docker 报告 (保持原样) ---
class DockerReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DockerReport
        fields = ['exit_code', 'stdout', 'compile_status', 'execution_time', 'status']


# --- 8. 提交记录序列化器 (🚀 核心适配最高分展示) ---
class SubmissionSerializer(serializers.ModelSerializer):
    # 嵌套作业信息
    assignment_info = AssignmentSerializer(source='assignment', read_only=True)

    # 嵌套 AI 评价 (展示本次提交的详情)
    ai_evaluation = AIEvaluationSimpleSerializer(read_only=True)

    # 嵌套 Docker 报告
    docker_report = DockerReportSerializer(read_only=True)

    student_name = serializers.ReadOnlyField(source='student.username')

    # 🚀 兼容性字段：计算属性
    ai_score = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            'id',
            'student',
            'student_name',
            'assignment',
            'assignment_info',
            'ai_evaluation',  # 🚀 这里面是“本次得分”
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
        保持逻辑一致性：
        如果 final_score 已由 GradingPipeline 计算并存入，直接返回。
        这确保了前端显示的 ai_score 字段永远是历史最高记录。
        """
        if obj.final_score is not None:
            return obj.final_score

        # 兜底逻辑：如果任务还没跑完，尝试从本次评价里取
        try:
            return obj.ai_evaluation.total_score
        except:
            return 0