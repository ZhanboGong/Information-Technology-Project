import json
import os
import zipfile
import io
import uuid
import shutil
import pandas as pd
import traceback
from apps.analytics.models import AIServiceLog
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.utils.encoding import escape_uri_path
from django.shortcuts import get_object_or_404
from django.db.models import Max, Count, Q
from django.db.models.functions import TruncDate
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# Import the model and serializer
from .models import User, Course, Assignment, Submission, AIEvaluation, KnowledgePoint, SystemConfiguration
from .serializers import (
    AssignmentSerializer,
    SubmissionSerializer,
    MyTokenObtainPairSerializer,
    CourseSerializer, KnowledgePointSerializer, UserProfileSerializer, ChangePasswordSerializer, SystemConfigurationSerializer
)
from .utils.ai_scorer import AIScorer
from .utils.project_analyzer import ProjectAnalyzer

# Sprint 2
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_assignment_grades(request, assignment_id):
    """
    Export all student grades of the specified assignment to Excel.
    This interface has a "dynamic column" generation logic, which can automatically adjust the table headers according to the Rubric dimensions specified in the job configuration.
    Business Logic:
    1. Permission Check: Only the instructors of this course or system administrators are allowed to export.
    2. Dynamic Column Headers: Extract the knowledge points (KnowledgePoint) associated with the assignment as an additional scoring column in Excel.
    3. Data Cleaning:
        - Automatically obtain the highest score submission record for each student (Submission).
        - Parse the JSON breakdown scores stored in AIEvaluation.ai_raw_feedback.
        - Handle edge cases such as no submission, parsing failure, etc.
    4. Formatting Output: Use Pandas to construct a DataFrame and use the openpyxl engine to generate an .xlsx file stream.
    :param request: DRF Request Object.
    :param assignment_id: The ID of the target assignment
    :return: Binary Excel file stream.
    """
    # 1. Obtain the assignment and verify the identity (Only the teacher of this assignment can export it)
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.user != assignment.teacher and not request.user.is_staff:
        return HttpResponse("You do not have the permission to export this transcript.", status=403)

    # 2. Obtain all the knowledge points (as dynamic column names in Excel) set for this assignment
    kp_list = assignment.knowledge_points.all()
    rubric_names = [kp.name for kp in kp_list]

    # 3. Prepare data container
    data = []
    # Obtain all the students who have chosen this course
    students = assignment.course.students.all()

    for student in students:
        # Obtain the submission record of this student's highest score for this assignment
        submission = Submission.objects.filter(
            student=student,
            assignment=assignment,
            status='completed'
        ).order_by('-final_score').first()

        row = {
            "学号": student.student_id_num or "无",
            "姓名": student.username,
            "班级": student.class_name or "无",
            "总分": submission.final_score if submission else "未提交"
        }

        # 4. Fill in the Rubric and break down the scores
        if submission:
            # Obtain the corresponding AI scoring record
            evaluation = AIEvaluation.objects.filter(submission=submission).first()
            scores_dict = {}

            if evaluation and evaluation.ai_raw_feedback:
                try:
                    # Attempt to parse the JSON stored in ai_raw_feedback
                    raw_json = json.loads(evaluation.ai_raw_feedback)
                    scores_dict = raw_json.get('scores', raw_json)
                except json.JSONDecodeError:
                    scores_dict = {}

            # Traverse the knowledge points set by the teacher and find the corresponding scores from the JSON.
            for kp_name in rubric_names:
                row[kp_name] = scores_dict.get(kp_name, "Parsing failed")
        else:
            # Set all dimensions to 0 or "/" when not committed.
            for kp_name in rubric_names:
                row[kp_name] = "/"

        data.append(row)

    # 5. Convert to DataFrame and export to Excel
    df = pd.DataFrame(data)

    # Adjust column order: Student number, name, class, total score, dimension 1, dimension 2...
    columns = ["学号", "姓名", "班级", "总分"] + rubric_names
    df = df.reindex(columns=columns)

    # 6. Construct the HttpResponse
    filename = f"Grades_{assignment.title}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # Handle Chinese file names
    response['Content-Disposition'] = f'attachment; filename="{filename.encode("utf-8").decode("ISO-8859-1")}"'

    df.to_excel(response, index=False, engine='openpyxl')

    return response


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
            except:
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
            except:
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
        AI intelligence suggests and automatically generates L2 level knowledge points.

        Business Background:
        When teachers publish assignments, they often need to manually define specific test points (L2 knowledge points).
        The interface uses AI to deeply analyze job requirements (Content) and scoring dimensions (Rubric) and generate them automatically
        Professional programming skill points to match and tie them to the current curriculum.

        Logical flow:
        1. Context Construction: Format the Rubric configuration items into AI-readable textual descriptions.
        2. Prompt-driven: Requires the AI to identify 3-5 core skills and output a rigid JSON structure.
        3. Result cleaning: Handle Markdown tags in AI responses and parse them into Python objects.
        4. Automatic persistence: Use 'get_or_create' to ensure that points with the same name in the same course and language are not repeated.
        5. Front-end synchronization: Returns data containing the database ID so that the front-end can be directly used for job association.
        :param request: Requests containing title, content, language, course_id, rubric_config.
        :return: A list of suggested knowledge points (with ids and existing/newly created identifiers).
        """
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        language = request.data.get('language', 'python')
        # Get the course ID (L2 must be bound to the course)
        course_id = request.data.get('course', request.data.get('course_id'))
        # Get the rating scale filled out in step 2
        rubric_config = request.data.get('rubric_config', {})

        if not content:
            return Response({"error": "Assignment requirements (content) cannot be empty."}, status=400)

        if not course_id:
            return Response({"error": "Course ID is required to generate L2 Knowledge Points."}, status=400)

        # 1. Convert the Rubric into a readable text description for AI reference
        rubric_desc = ""
        if rubric_config and 'items' in rubric_config:
            rubric_desc = "\n".join([
                f"- Assessment Dimension: {item.get('criterion')} (Weight: {item.get('weight')}%)"
                for item in rubric_config.get('items', [])
            ])

        scorer = AIScorer()

        # 2. Construct Prompt
        prompt = f"""
            You are a professional programming teaching assistant. Please identify 3-5 core programming skills (L2 level) that students must master to complete this task.

            [Assignment Title]:{title}
            [Assignment Requirements]:{content}
            [Programming Language]:{language}
            [Grading Standards (Rubric)]:
            {rubric_desc or "Standard coding practices"}

            Requirements:
            1. Knowledge point names (name) should be concise (e.g., Recursion, Class Inheritance, Exception Handling).
            2. The detailed assessment logic (description) should explain how students should apply the technology based on the requirements and rubric to achieve high scores.
            3. Output the result directly in JSON format. Do not include Markdown tags like ```json.

            JSON Format:
            {{
                "suggested_kps": [
                    {{"name": "Skill Name", "description": "Detailed assessment logic说明"}},
                    ...
                ]
            }}
            """

        try:
            # 3. Ask the AI and clean the results
            raw_res = scorer.ask(prompt)
            clean_json = raw_res.replace('```json', '').replace('```', '').strip()
            suggestions = json.loads(clean_json)

            # 4. Automatic persistence: The suggested knowledge points are written to the database
            course_obj = Course.objects.get(id=course_id)
            final_suggestions = []

            for kp_data in suggestions.get('suggested_kps', []):
                # If the KP with the same name, language, and course already exists, it will be obtained, and if not, it will be created
                kp, created = KnowledgePoint.objects.get_or_create(
                    name=kp_data['name'],
                    course=course_obj,
                    language=language.lower(),
                    defaults={
                        'description': kp_data['description'],
                        'category': 'L2',
                        'is_system': False
                    }
                )
                # Combine the data returned to the frontend, including the database ID
                final_suggestions.append({
                    "id": kp.id,
                    "name": kp.name,
                    "description": kp.description,
                    "is_new": created
                })

            # 5. Return results
            return Response({
                "suggested_kps": final_suggestions
            })

        except Course.DoesNotExist:
            return Response({"error": "The specified course does not exist."}, status=404)
        except json.JSONDecodeError:
            print(f"Failed to parse AI response: {raw_res}")
            return Response({"error": "AI returned an invalid format. Please try again."}, status=500)
        except Exception as e:
            print(f"AI KP Generation Error: {str(e)}")
            return Response({"error": f"AI generation failed: {str(e)}"}, status=500)

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
        # 如果是老师创建，可以根据需求在这里自动补充逻辑（可选）
        serializer.save()

    # 也可以增加一个过滤逻辑，让老师默认只能看到自己课程的 KP
    def get_queryset(self):
        qs = super().get_queryset()
        # 如果不是管理员，根据课程过滤（可选，取决于你的设计意图）
        return qs


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
        serializer.save()

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

    @action(detail=False, methods=['get'], url_path='download-template')
    def download_template(self, request):
        """
        提供学生导入模板下载
        """
        # 定义模板表头（需与 import_students 中的逻辑对应）
        columns = ['student_id', 'name', 'class']

        # 创建示例数据（可选，给用户参考）
        sample_data = [
            ['20260001', 'John Doe', 'Class A'],
            ['20260002', 'Jane Smith', 'Class B']
        ]

        df = pd.DataFrame(sample_data, columns=columns)

        # 使用 BytesIO 在内存中生成 Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')

        output.seek(0)

        # 构造响应
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
            return Response({"message": "System configuration has been updated.", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
                "action": f"学生 {sub.student.username} 提交了作业: {sub.assignment.title}",
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

        if role and role != 'all':
            queryset = queryset.filter(role=role)

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

        :param request:
        :param pk:
        :return:
        """
        user = self.get_object()
        # 重置密码为学号/工号，或固定默认值
        default_pwd = user.student_id_num if user.student_id_num else "123456"
        user.set_password(default_pwd)
        user.save()
        return Response({"message": f"密码已重置为: {default_pwd}"})

    def perform_create(self, serializer):
        """
        在保存用户前，进行业务逻辑处理：
        1. 默认密码设为学号/工号
        2. 如果没传 student_id_num，默认密码设为 123456
        """
        student_id = self.request.data.get('student_id_num', '')
        password = make_password(student_id if student_id else "123456")

        # 强制将 username 设为 student_id_num (符合你登录系统的设计)
        serializer.save(
            password=password,
            username=student_id if student_id else serializer.validated_data.get('username')
        )


class SystemMonitorView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        import random
        # 1. 模拟系统节点状态 (保持不变)
        nodes = [
            {'name': 'Core API Server', 'status': 'Online', 'load': random.randint(20, 40),
             'desc': 'Django Gunicorn Stack'},
            {'name': 'Celery Worker 01', 'status': 'Online', 'load': random.randint(5, 30), 'desc': 'Grading Runner'},
            {'name': 'Redis Broker', 'status': 'Online', 'load': random.randint(1, 5), 'desc': 'Message Queue'},
        ]

        # 2. 获取最近任务 (保持不变)
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

        # 3. 【核心增强】从 AIServiceLog 获取真实 AI 性能数据
        # 获取最近 20 条日志用于绘制趋势图
        ai_logs = AIServiceLog.objects.order_by('-created_at')[:20]

        # 计算平均延迟和 Token 总量
        if ai_logs.exists():
            avg_latency = sum(log.response_time for log in ai_logs) / ai_logs.count()
            total_tokens_24h = sum(log.total_tokens for log in ai_logs)  # 简化逻辑，实际可按时间过滤

            # 构造趋势图数据 (response_time)
            latency_history = [int(log.response_time * 1000) for log in reversed(ai_logs)]  # 转为毫秒
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
    Admin端：获取系统审计与AI调用日志
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        # 获取最近的 50 条 AI 调用日志
        logs = AIServiceLog.objects.select_related().all().order_by('-created_at')[:50]

        log_data = []
        for log in logs:
            log_data.append({
                "id": log.id,
                "service": log.service_name,
                "endpoint": log.endpoint,
                "tokens": log.total_tokens,
                "latency": f"{int(log.response_time * 1000)}ms",
                "status": log.status_code,
                "time": log.created_at
            })

        return Response(log_data)