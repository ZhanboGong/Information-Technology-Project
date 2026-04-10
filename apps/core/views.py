import os
import zipfile
import io
import uuid
import shutil
import pandas as pd
import traceback
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.utils.encoding import escape_uri_path
from django.db.models import Max
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# Import the model and serializer
from .models import User, Course, Assignment, Submission, AIEvaluation, KnowledgePoint
from .serializers import (
    AssignmentSerializer,
    SubmissionSerializer,
    MyTokenObtainPairSerializer,
    CourseSerializer, KnowledgePointSerializer, UserProfileSerializer, ChangePasswordSerializer
)
from .utils.ai_scorer import AIScorer
from .utils.project_analyzer import ProjectAnalyzer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_global_assignment_reminders(request):
    """
    Get the assessment deadline warning on the student's dashboard page.

    This interface is dedicated to the dashboard page display, and the logic is as follows:
    1. Role filtering: Perform only for users whose role is 'student'.
    2. Time window: Filter the assessments that are due in the next 7 days (within a week) from the current time.
    3. Status filtering: Automatically excludes assignments that students have submitted successfully or are in process, and only keeps "to be done" tasks.
    4. Urgency: Results are sorted in ascending order by deadline (most urgent first).
    :param request: DRF request object, which should contain the authenticated user instance.
    :return: A list containing alert details. If there is no reminder or the user is not a student, an empty list is returned.
    """
    user = request.user
    # Only the student role needs to be reminded
    if user.role != 'student':
        return Response([])

    now = timezone.now()
    one_week_later = now + timedelta(days=7)

    # 1. Find all assignments that are due within a week for a student's chosen course
    upcoming_assignments = Assignment.objects.filter(
        course__students=user,
        deadline__range=(now, one_week_later)
    ).select_related('course')  # 使用 select_related 优化查询

    reminders = []
    for assignment in upcoming_assignments:
        # 2. Check if the student already has a "done" or "in progress" submission for the assignment
        has_submitted = Submission.objects.filter(
            student=user,
            assignment=assignment
        ).exclude(status='failed').exists()

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
                "category": assignment.category
            })

    # Sort by urgency (closest deadline first)
    reminders.sort(key=lambda x: x['deadline'])

    return Response(reminders)

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
        return request.user.is_authenticated and request.user.role == 'teacher'


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
    def perform_create(self, serializer):
        """
        Save the newly created assignment instance, and associate the teacher and the knowledge point.
        This method overrides the parent class's perform_create to ensure that the currently logged in teacher is automatically logged in when the job is created
        Set as the owner of the job and handle many-to-many relationships (KnowledgePoints) manually.
        :param serializer: Validated job serializer instance
        :return: none
        """
        kp_ids = self.request.data.get('knowledge_points', [])
        assignment = serializer.save(teacher=self.request.user)
        if kp_ids:
            assignment.knowledge_points.set(kp_ids)

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
            evaluation.total_score = new_score
            evaluation.feedback = new_feedback
            evaluation.teacher_reviewed = True
            evaluation.is_published = True
            evaluation.save()
            sub = evaluation.submission
            sub.final_score = new_score
            sub.save()
            return Response({"message": "The results have been updated and published"})
        except AIEvaluation.DoesNotExist:
            return Response({"error": "Evaluation records do not exist"}, status=404)

    @action(detail=False, methods=['post'], url_path='suggest-kps')
    def suggest_knowledge_points(self, request):
        """

        :param request:
        :return:
        """
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        language = request.data.get('language', 'python')

        if not content:
            return Response({"error": "作业要求（描述）不能为空"}, status=400)

        scorer = AIScorer()
        # 优化 Prompt：明确要求不要包含 Markdown 代码块标签
        prompt = f"""
            你是一名专业的编程教学助理。请根据以下作业任务，识别出学生完成该作业需要掌握的 3-5 个核心编程知识点（L2 级别）。

            作业标题：{title}
            作业要求：{content}
            编程语言：{language}

            要求：
            1. 知识点名称要简练（如：递归调用、类继承、异常处理）。
            2. 详细考核逻辑应说明学生需要如何实现或运用该技术点。
            3. 直接输出 JSON 结果，不要包含任何 Markdown 格式的标签（如 ```json）。

            JSON 格式如下：
            {{
                "suggested_kps": [
                    {{"name": "知识点名称", "description": "详细考核逻辑说明"}},
                    ...
                ]
            }}
            """

        try:
            raw_res = scorer.ask(prompt)

            # 清洗 AI 可能返回的 Markdown 标签
            if "```json" in raw_res:
                raw_res = raw_res.split("```json")[-1].split("```")[0].strip()
            elif "```" in raw_res:
                raw_res = raw_res.split("```")[-1].split("```")[0].strip()

            import json
            suggestions = json.loads(raw_res)
            return Response(suggestions)
        except json.JSONDecodeError:
            print(f"❌ AI 返回内容无法解析: {raw_res}")
            return Response({"error": "AI 返回格式异常，请稍后再试"}, status=500)
        except Exception as e:
            return Response({"error": f"AI 生成失败: {str(e)}"}, status=500)

    @action(detail=False, methods=['get'], url_path='download-submission')
    def download_single_submission(self, request):
        """
        Download specific individual student submissions.

        The interface implements automatic renaming logic: the original messy filename is converted to the standard format of "student_name_assignment title".
        It is greatly convenient for teachers to archive and organize after downloading.

        Permissions and Security:
            - Force a 'assignment__teacher=request.user' check to make sure teachers can only download student work from their own course.
            - Use 'escape_uri_path' to make sure Chinese filenames don't get messy in Chrome/Firefox etc.
        :param request: DRF request object. You need to include the 'submission_id' in query_params.
        :return:
            FileResponse: Binary file stream
            Response: 400 (parameter missing) or 404 (record does not exist/has no access)
        """
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response({"error": "缺少 submission_id 参数"}, status=400)

        try:
            # Permission isolation query: Check the teacher of the assignment across the table by double underscores
            submission = Submission.objects.get(id=submission_id, assignment__teacher=request.user)
            file_handle = submission.file.open()

            # Construct a normalized download filename
            ext = os.path.splitext(submission.file.name)[1]
            # Format: Student number _ name _ assignment title. Extensions
            filename = f"{submission.student.student_id_num}_{submission.student.first_name}_{submission.assignment.title}{ext}"
            # 3. Build the file response object
            response = FileResponse(file_handle, content_type='application/octet-stream')
            # RFC 5987: Use the filename*=utf-8 "syntax for non-ASCII filenames
            response['Content-Disposition'] = f"attachment; filename*=utf-8''{escape_uri_path(filename)}"
            return response
        except Submission.DoesNotExist:
            return Response({"error": "No relevant commit record was found or access was not granted"}, status=404)

    @action(detail=True, methods=['get'], url_path='download-all')
    def download_all_submissions(self, request, pk=None):
        """
        Download the latest submission of all students under a given assignment in bulk and package it as ZIP.

        Business logic:
        1. Deduplicate: Use Django's 'Max('id')' aggregation function to filter out each student's "last" submission for that assignment.
        2. Memory compression: Using 'IO. BytesIO' to complete the compression process in memory, does not occupy disk IO, and has fast response time.
        3. Structural reorganization: In the ZIP package, the files are renamed to the "student number _ name" format, which is convenient for bulk import into other scoring software or archiving.
        :param request: DRF request object.
        :param pk: The ID of the target job.
        :return: Contains the response in a ZIP archive.
        """
        assignment = self.get_object()
        # Get the last submission for each student under that assignment
        from django.db.models import Max
        latest_submissions_ids = Submission.objects.filter(assignment=assignment).values('student').annotate(
            latest_id=Max('id')).values_list('latest_id', flat=True)
        submissions = Submission.objects.filter(id__in=latest_submissions_ids)

        if not submissions.exists():
            return Response({"error": "There is no record of submission"}, status=404)

        # Create a ZIP file in memory
        byte_io = io.BytesIO()
        with zipfile.ZipFile(byte_io, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for sub in submissions:
                if sub.file and os.path.exists(sub.file.path):
                    ext = os.path.splitext(sub.file.name)[1]
                    # ZIP file name: Student number _ Name. Suffix
                    arc_name = f"{sub.student.student_id_num}_{sub.student.first_name}{ext}"
                    zip_file.write(sub.file.path, arcname=arc_name)

        byte_io.seek(0)
        zip_filename = f"{assignment.title}_全部提交.zip"

        response = HttpResponse(byte_io, content_type='application/zip')
        response['Content-Disposition'] = f"attachment; filename*=utf-8''{escape_uri_path(zip_filename)}"
        return response


class KnowledgePointViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Knowledge point dictionary query view set.
    The interface acts as a common dictionary table that allows all log in users, teachers and students, to view a list of knowledge points within the system.
    Since it is only used for data retrieval, ReadOnlyModelViewSet is used to disable all additions, deletions and changes.
    Permission Restrictions: Restrict access to IsAuthenticated users only.
    """
    queryset = KnowledgePoint.objects.all()
    serializer_class = KnowledgePointSerializer
    permission_classes = [permissions.IsAuthenticated]


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
        serializer.save(teacher=self.request.user)

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

            course.students.remove(*students_to_remove)

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
                            'password': make_password(sid)
                        }
                    )

                    if created:
                        created_count += 1

                    if target_course:
                        if not target_course.students.filter(id=user.id).exists():
                            target_course.students.add(user)
                            enrolled_count += 1

            return Response({
                "message": f"Import success: {created_count} new student accounts are created and {enrolled_count} people are added to the course."
            })

        except Course.DoesNotExist:
            return Response({"error": "The specified course does not exist or you do not have permission to operate it."}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"Failed table parsing: {str(e)}"}, status=400)


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

            # 1. Permission and frequency verification
            if not assignment.course.students.filter(id=student.id).exists():
                return Response({"error": "You are not authorized to submit this assessment"}, status=403)

            existing_count = Submission.objects.filter(student=student, assignment=assignment).count()
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
                attempt_number=existing_count + 1,
                sub_type=calculated_sub_type,
                status='pending'
            )

            # 4. Enter Pipeline orchestration
            self.run_agent_pipeline(submission)
            return Response({"message": "Submission successful. System processing in progress..."}, status=201)

        except Exception as e:
            print(f"❌ ViewSet Create Error: {str(e)}")
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


class UserProfileViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def manage_me(self, request):
        """获取或更新当前登录用户的信息"""
        instance = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        # 更新逻辑
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """修改密码"""
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        # 校验旧密码
        if not user.check_password(serializer.data.get('old_password')):
            return Response({"error": "旧密码错误"}, status=status.HTTP_400_BAD_REQUEST)

        # 设置新密码
        user.set_password(serializer.data.get('new_password'))
        user.save()
        return Response({"message": "密码修改成功"})
