import json
import traceback
from django.db.models import Avg
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.models import Course, Assignment, Submission, AIEvaluation, KnowledgePoint


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
        """
        Teacher end: Class-wide academic performance statistics dashboard.
        Business Logic:
        1. Permission Check: Strictly verify whether the requester has the 'teacher' role.
        2. Performance Evolution Trend (History): Statistically calculate the average class score of all previous assignments in this course, reflecting the fluctuations in teaching effectiveness.
        3. Class Capability Radar (Radar): Summarize the knowledge point scores from all AI evaluations in the class (without hierarchical divisions),
        constructing an overall skill map of the class.
        4. Visual Noise Reduction (Smart Thinning): When there are too many knowledge point dimensions, automatically execute the "Two-Extremes Filtering Algorithm",
        retaining only 4 dimensions with the highest and lowest scores each, helping teachers quickly identify "teaching achievements" and "weak links".
        :param pk: Course ID
        """
        if request.user.role != 'teacher':
            return Response({"error": "Insufficient permissions"}, status=403)

        try:
            course = Course.objects.get(id=pk)
            assignments = Assignment.objects.filter(course=course).order_by('created_at')

            # Statistics of Homework Trends
            trend = []
            for asm in assignments:
                res = Submission.objects.filter(
                    assignment=asm,
                    ai_evaluation__is_published=True
                ).aggregate(avg=Avg('final_score'))
                avg_score = res['avg'] or 0

                trend.append({
                    "task": asm.title,
                    "score": round(float(avg_score), 1)
                })

            # Class Knowledge Summary (L1 + L2)
            kp_mastery = {}
            evals = AIEvaluation.objects.filter(submission__assignment__course=course, is_published=True)

            for ev in evals:
                kp_data = self._extract_kp_scores(ev)
                for kp_name, score in kp_data.items():
                    clean_name = kp_name.split('(')[0].strip()
                    kp_mastery.setdefault(clean_name, []).append(float(score))

            # Calculate the average score
            raw_averages = {name: round(sum(scores) / len(scores), 1) for name, scores in kp_mastery.items()}

            if len(raw_averages) > 8:
                sorted_items = sorted(raw_averages.items(), key=lambda x: x[1])
                # Select the 4 with the lowest scores and the 4 with the highest scores
                selected_data = dict(sorted_items[:4] + sorted_items[-4:])
                processed_radar = selected_data
            else:
                processed_radar = raw_averages

            return Response({
                "summary": {
                    "average_score": round(float(evals.aggregate(avg=Avg('total_score'))['avg'] or 0), 1),
                    "total_submissions": evals.count()
                },
                "history": trend,
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
    