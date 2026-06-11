import json
import re
import traceback
from django.db.models import Avg, Max, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.models import Course, Assignment, Submission, AIEvaluation, KnowledgePoint
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from apps.core.utils.ai_scorer import AIScorer


class AnalyticsViewSet(viewsets.ViewSet):
    """
    Deep Learning Academic Analysis Center.
    Provide differentiated data insights for both the teacher end and the student end:
    - Teacher end (Course Dashboard): Comprehensive summary of class assignment performance, analysis of knowledge point mastery trends, and assistance in teaching decisions.
    - Student end (Personal Analytics): In-depth analysis of individual weak points, comparison with the class average level.
    Core features:
    1. Robust data extraction: Supports bidirectional extraction of scores from structured fields and raw AI JSON responses.
    2. Intelligent visualization optimization: Automatically performs "dichotomous simplification" when there are too many knowledge points, ensuring the readability of the radar chart.
    3. Real-time aggregation: Utilizes Django aggregation functions (Avg, Count) to achieve millisecond-level data summarization.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _extract_kp_scores(self, ev_obj):
        """
        Internal support: Utilize multiple strategies to extract knowledge and scoring data.
        Due to the volatility of the AI output, the scores may be stored in `scores.kp_scores`, or they may be hidden within the Markdown JSON block of `raw_response`. This method implements fault-tolerant parsing.
        """
        kp_data = ev_obj.scores.get('kp_scores', {}) if isinstance(ev_obj.scores, dict) else {}

        if not kp_data and hasattr(ev_obj, 'raw_response') and ev_obj.raw_response:
            try:
                raw_text = ev_obj.raw_response.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                parsed_json = json.loads(raw_text)
                kp_data = parsed_json.get('kp_scores', {})
            except Exception:
                pass
        return kp_data if isinstance(kp_data, dict) else {}

    @action(detail=True, methods=['get'], url_path='course-dashboard')
    def course_dashboard(self, request, pk=None):
        if request.user.role != 'teacher':
            return Response({"error": "Insufficient permissions"}, status=403)

        from django.db.models import Avg, Max, Count
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from datetime import timedelta

        try:
            course = Course.objects.get(id=pk)
            assignments = Assignment.objects.filter(course=course).order_by('created_at')

            # 1. Historical trend of assignment score (take the highest score of each student)
            trend = []
            for asm in assignments:
                student_best_scores = Submission.objects.filter(
                    assignment=asm,
                    ai_evaluation__is_published=True
                ).values('student').annotate(max_score=Max('final_score'))

                if student_best_scores:
                    avg_score = sum(item['max_score'] for item in student_best_scores) / len(student_best_scores)
                else:
                    avg_score = 0

                trend.append({
                    "task": asm.title,
                    "score": round(float(avg_score), 1)
                })

            # 2. Daily submission activity
            two_weeks_ago = timezone.now() - timedelta(days=14)
            daily_stats = Submission.objects.filter(
                assignment__course=course,
                created_at__gte=two_weeks_ago
            ).annotate(day=TruncDate('created_at')).values('day').annotate(count=Count('id')).order_by('day')

            submission_trend = [{"date": item['day'].strftime('%m-%d'), "count": item['count']} for item in daily_stats]

            # 3. Skill radar
            all_evals = AIEvaluation.objects.filter(submission__assignment__course=course,
                                                    is_published=True).select_related('submission')
            kp_mastery = {}
            for ev in all_evals:
                kp_data = self._extract_kp_scores(ev)
                for kp_name, score in kp_data.items():
                    clean_name = kp_name.split('(')[0].strip()
                    kp_mastery.setdefault(clean_name, []).append(float(score))

            raw_averages = {name: round(sum(scores) / len(scores), 1) for name, scores in kp_mastery.items()}
            processed_radar = raw_averages
            if len(raw_averages) > 8:
                sorted_items = sorted(raw_averages.items(), key=lambda x: x[1])
                processed_radar = dict(sorted_items[:4] + sorted_items[-4:])

            # --- 4. Summary mean score calculation ---
            valid_scores = [t['score'] for t in trend if t['score'] > 0]
            total_avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0

            return Response({
                "summary": {
                    "average_score": round(float(total_avg), 1),
                    "total_submissions": all_evals.count()
                },
                "history": trend,
                "submission_trend": submission_trend,
                "l2_knowledge_radar": processed_radar
            })

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['get'], url_path='student-profile')
    def student_profile(self, request):
        """
        Student end: Personal learning situation overview and growth records.
        Business logic (following the strict classification standards defined by the team leader):
        1. Vertical growth curve: Retrieve all published assessment records of this student and display the evolution process of their individual scores.
        2. Penetrative classification radar:
        - L1 General Skills (Radar L1): Only display core programming competencies (such as grammar, logic) that match the `is_system=True` entries in the database.
        - L2 Special Skills (Radar L2): Display specific exam points that are not system-predefined and are tailored for specific assignments.
        3. Strict matching verification: The knowledge point names output by AI must have corresponding records in the `KnowledgePoint` table to be included in the radar chart,
        ensuring the authority and rigor of the student data.
        :return: It includes the growth history, classification radar chart and summary of average scores.
        """
        user = request.user
        evals = AIEvaluation.objects.filter(
            submission__student=user,
            is_published=True
        ).select_related('submission__assignment').order_by('created_at')

        if not evals.exists():
            return Response({
                "summary": {"average_score": 0, "total_completed": 0},
                "radar_l1_general": {},
                "radar_l2_special": {},
                "history": []
            })

        history = [{
            "task": ev.submission.assignment.title,
            "score": float(ev.total_score),
            "date": ev.created_at.strftime('%m-%d')
        } for ev in evals]

        l1_radar, l2_radar = {}, {}

        for ev in evals:
            kp_data = self._extract_kp_scores(ev)
            for name, score in kp_data.items():
                kp_obj = KnowledgePoint.objects.filter(name=name).first()
                if kp_obj:
                    target = l1_radar if kp_obj.is_system else l2_radar
                    target.setdefault(name, []).append(float(score))

        return Response({
            "history": history,
            "radar_l1_general": {k: round(sum(v) / len(v), 1) for k, v in l1_radar.items()},
            "radar_l2_special": {k: round(sum(v) / len(v), 1) for k, v in l2_radar.items()},
            "summary": {
                "total_completed": evals.count(),
                "average_score": round(float(evals.aggregate(avg=Avg('total_score'))['avg'] or 0), 1)
            }
        })

    @action(detail=False, methods=['post'], url_path='get-study-resource')
    def get_study_resource(self, request):
        """
        Provides targeted video resources and study tips.
        Logic Workflow:
        1. Intent Identification: Captures the Knowledge Point (KP) the student is struggling with.
        2. AI Query Optimization: Uses the LLM to transform a raw KP name into a professional
           educational search query and generates a contextual study tip.
        3. YouTube API Integration: Attempts to fetch the top-rated educational video
           programmatically using the YouTube Data API.
        4. Robust Fallback: If the API fails or the key is missing, it constructs a direct
           YouTube search URL so the student is never left without resources.
        :param request: A JSON object containing the video URL and an actionable study tip.
        :return:
        """
        kp_name = request.data.get('kp_name')
        if not kp_name:
            return Response({"error": "Knowledge point name is required"}, status=400)

        scorer = AIScorer()

        # Ask the AI to act as a librarian to find the best content
        prompt = f"""
        The student is struggling with: "{kp_name}".
        Generate a YouTube search query to find a good tutorial video for this topic.
        Keep it short and specific (2-5 words).

        Return a JSON object:
        {{
            "query": "Java LinkedList tutorial",
            "study_tip": "One sentence actionable advice..."
        }}
        """

        try:
            # Step 1: Call the LLM to get an optimized search query
            response = scorer.client.chat.completions.create(
                model=scorer.model,
                messages=[
                    {"role": "system", "content": "Output ONLY a JSON object."},
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'},
                temperature=0
            )

            # Step 2: Clean and parse the AI response
            raw_res = response.choices[0].message.content
            clean_json = re.sub(r'```json\s?|\s?```', '', raw_res).strip()
            data = json.loads(clean_json)

            search_query = data.get('query', kp_name)
            study_tip = data.get('study_tip', "Keep practicing to master this concept!")

        except Exception:
            # Fallback if the LLM call fails
            search_query = kp_name
            study_tip = "Try searching for specific tutorials and building small projects."

        # Step 3: Integrate with YouTube Data API v3
        import os, requests as req
        YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

        if YOUTUBE_API_KEY:
            try:
                yt_response = req.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": f"{search_query} tutorial",
                        "type": "video",
                        "maxResults": 1,
                        "key": YOUTUBE_API_KEY,
                        "videoCategoryId": "28"
                    },
                    timeout=5
                )
                items = yt_response.json().get('items', [])
                if items:
                    video_id = items[0]['id']['videoId']
                    return Response({
                        "kp_name": kp_name,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "study_tip": study_tip
                    })
            except Exception:
                pass

        # Step 4: Final Fallback - Generate a direct search result link
        fallback_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}+tutorial"
        return Response({
            "kp_name": kp_name,
            "url": fallback_url,
            "study_tip": study_tip
        })

    @action(detail=False, methods=['get'], url_path='knowledge-heatmap')
    def knowledge_heatmap(self, request):
        """
        Heatmap of knowledge point mastery degree: two-dimensional matrix of task dimension × knowledge point dimension.
        Only the assessment record with the highest score is taken for each assignment.
        """
        user = request.user
        evals = AIEvaluation.objects.filter(
            submission__student=user,
            is_published=True
        ).select_related('submission__assignment').order_by('created_at')

        if not evals.exists():
            return Response({"assignments": [], "knowledge_points": [], "matrix": []})

        assignments = []
        all_kps = set()
        matrix = []

        # Grouping by Assignment, each job takes only the one with the highest score
        seen_assignments = {}
        for ev in evals:
            asm_id = ev.submission.assignment.id
            if asm_id not in seen_assignments or ev.total_score > seen_assignments[asm_id].total_score:
                seen_assignments[asm_id] = ev

        for asm_id, ev in seen_assignments.items():
            assignment_title = ev.submission.assignment.title
            kp_data = self._extract_kp_scores(ev)
            if not kp_data and isinstance(ev.scores, dict):
                kp_data = ev.scores.get('kp_scores', {})

            row = {"assignment": assignment_title, "scores": {}}
            for kp_name, score in kp_data.items():
                all_kps.add(kp_name)
                row["scores"][kp_name] = round(float(score), 1)
            matrix.append(row)

            if assignment_title not in assignments:
                assignments.append(assignment_title)

        return Response({
            "assignments": assignments,
            "knowledge_points": sorted(list(all_kps)),
            "matrix": matrix
        })

    @action(detail=False, methods=['get'], url_path='course-ranking')
    def course_ranking(self, request):
        """
        The rank of the students in each course.
        Algorithm: For each assignment, take the student's highest score, then calculate the course mean, and rank by the mean.
        """
        from apps.core.models import Course, Submission
        from django.db.models import Max

        user = request.user
        courses = Course.objects.filter(students=user)

        rankings = []
        for course in courses:
            # Get all assignments for this course
            assignments = course.assignments.all()
            if not assignments.exists():
                continue

            # Get the highest score for each assignment for all students in the course
            student_best = Submission.objects.filter(
                assignment__course=course,
                status='completed'
            ).values('student', 'assignment').annotate(
                best=Max('final_score')
            )

            # Group by student and calculate course mean
            from collections import defaultdict
            student_scores = defaultdict(list)
            for item in student_best:
                student_scores[item['student']].append(float(item['best'] or 0))

            # Calculate the course mean for each student
            student_avgs = []
            for sid, scores in student_scores.items():
                avg = sum(scores) / len(scores) if scores else 0
                student_avgs.append({"student_id": sid, "avg": round(avg, 1), "assignment_count": len(scores)})

            # Calculate the course mean for each student
            student_avgs.sort(key=lambda x: x['avg'], reverse=True)

            # Find the rank of the current student
            rank = 0
            my_avg = 0
            my_assignments = 0
            total_students = len(student_avgs)
            for idx, item in enumerate(student_avgs, 1):
                if item['student_id'] == user.id:
                    rank = idx
                    my_avg = item['avg']
                    my_assignments = item['assignment_count']
                    break

            if rank == 0:
                continue

            percentile = round((1 - rank / total_students) * 100, 1) if total_students > 0 else 0

            rankings.append({
                "course_id": course.id,
                "course_name": course.name,
                "rank": rank,
                "total_students": total_students,
                "my_avg_score": my_avg,
                "assignments_completed": my_assignments,
                "total_assignments": assignments.count(),
                "percentile": percentile
            })

        return Response({"rankings": rankings})

    @action(detail=False, methods=['get'], url_path='kp-growth-trend')
    def kp_growth_trend(self, request):
        """
        Trend of score change for each knowledge point (sorted by assignment time).
        The front end can be used to draw multi-line charts.
        """
        user = request.user
        evals = AIEvaluation.objects.filter(
            submission__student=user,
            is_published=True
        ).select_related('submission__assignment').order_by('created_at')

        if not evals.exists():
            return Response({"labels": [], "series": {}})

        labels = []  # X-axis: job name
        series = {}  # One line per knowledge point

        for ev in evals:
            title = ev.submission.assignment.title
            kp_data = self._extract_kp_scores(ev)
            if not kp_data and isinstance(ev.scores, dict):
                kp_data = ev.scores.get('kp_scores', {})

            if title not in labels:
                labels.append(title)

            for kp_name, score in kp_data.items():
                if kp_name not in series:
                    series[kp_name] = []
                series[kp_name].append(round(float(score), 1))

        return Response({
            "labels": labels,
            "series": series
        })



