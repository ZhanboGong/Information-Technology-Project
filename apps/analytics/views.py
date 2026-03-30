import json
import traceback
from django.db.models import Avg
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.models import Course, Assignment, Submission, AIEvaluation, KnowledgePoint


class AnalyticsViewSet(viewsets.ViewSet):
    """
    📊 深度学情分析中心：
    - 学生端：穿透分析（严格匹配数据库 L1/L2）
    - 教师端：班级洞察（全量汇总 L1/L2 + 智能精简）
    """
    permission_classes = [permissions.IsAuthenticated]

    def _extract_kp_scores(self, ev_obj):
        """
        🚀 内部辅助方法：提取知识点分值（兼容字典及原始文本）
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

    # --- 1. 教师端：班级洞察（全量汇总智能版） ---
    @action(detail=True, methods=['get'], url_path='course-dashboard')
    def course_dashboard(self, request, pk=None):
        if request.user.role != 'teacher':
            return Response({"error": "权限不足"}, status=403)

        try:
            course = Course.objects.get(id=pk)
            assignments = Assignment.objects.filter(course=course).order_by('created_at')

            # 作业趋势统计
            trend = []
            for asm in assignments:
                # 显式命名 'avg' 防止字段名匹配错误
                res = Submission.objects.filter(
                    assignment=asm,
                    ai_evaluation__is_published=True
                ).aggregate(avg=Avg('final_score'))
                avg_score = res['avg'] or 0

                trend.append({
                    "task": asm.title,
                    "score": round(float(avg_score), 1)
                })

            # 班级知识点汇总 (L1 + L2)
            kp_mastery = {}
            evals = AIEvaluation.objects.filter(submission__assignment__course=course, is_published=True)

            for ev in evals:
                kp_data = self._extract_kp_scores(ev)
                for kp_name, score in kp_data.items():
                    # 🚀 教师端逻辑：全量汇总，去掉 L2 过滤
                    clean_name = kp_name.split('(')[0].strip()
                    kp_mastery.setdefault(clean_name, []).append(float(score))

            # 计算平均分
            raw_averages = {name: round(sum(scores) / len(scores), 1) for name, scores in kp_mastery.items()}

            # 🚀 智能精简：如果全班维度 > 8 个，挑选最有代表性的展示，防止雷达图密恐
            if len(raw_averages) > 8:
                sorted_items = sorted(raw_averages.items(), key=lambda x: x[1])
                # 选取分数最低的 4 个和最高的 4 个
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

    # --- 2. 学生端：个人分析（组长要求的严格匹配版） ---
    @action(detail=False, methods=['get'], url_path='student-profile')
    def student_profile(self, request):
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
                # 🚀 组长逻辑：必须在 KnowledgePoint 表中有记录才分类显示
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