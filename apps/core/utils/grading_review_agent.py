class GradingReviewAgent:
    """
    AI Scoring Consistency Review Agent.

    Performs rule-engine checks on AI scoring results after grading is completed,
    detecting four categories of anomalies: KP-Rubric contradictions, inflated
    completion rates, feedback-score mismatches, and excessive dimension dispersion.
    Flagged issues trigger a second scoring pass.
    """

    def review(self, eval_data):
        """
        Review AI scoring results.
        :param eval_data: dict returned by AIScorer.evaluate_code
        :return: (passed: bool, issues: list[str], suggestion: str or None)
        """
        issues = []

        completion_rate = eval_data.get('completion_rate', 100)
        kp_scores = eval_data.get('kp_scores', {})
        scores = eval_data.get('scores', {})
        feedback = eval_data.get('feedback', '')
        total_score = eval_data.get('total_score', 0)

        # Rule 1: KP-Rubric contradiction
        if kp_scores and scores:
            kp_avg = sum(float(v) for v in kp_scores.values()) / len(kp_scores)
            rubric_values = [float(v) for v in scores.values()]
            rubric_max = max(rubric_values) if rubric_values else 0
            if kp_avg < 50 and rubric_max > 80:
                issues.append(
                    f"KP-Rubric mismatch: KP avg ({kp_avg:.1f}) < 50 "
                    f"but Rubric max ({rubric_max:.1f}) > 80"
                )

        # Rule 2: Completion-KP contradiction
        if kp_scores and completion_rate > 80:
            low_kp_count = sum(1 for v in kp_scores.values() if float(v) < 40)
            if low_kp_count >= 2:
                issues.append(
                    f"Completion-KP mismatch: completion_rate={completion_rate} "
                    f"but {low_kp_count} KPs < 40"
                )

        # Rule 3: Feedback-score contradiction
        negative_keywords = [
            'missing', 'failed', 'not implemented', 'error', 'incorrect',
            'does not compile', 'throws exception', 'bug', 'incomplete'
        ]
        negative_count = sum(1 for kw in negative_keywords if kw in feedback.lower())
        if negative_count >= 3 and total_score > 85:
            issues.append(
                f"Feedback-score mismatch: {negative_count} negative signals "
                f"in feedback but total_score={total_score}"
            )

        # Rule 4: Excessive rubric dispersion
        if scores and len(scores) >= 3:
            score_values = [float(v) for v in scores.values()]
            mean = sum(score_values) / len(score_values)
            variance = sum((x - mean) ** 2 for x in score_values) / len(score_values)
            std = variance ** 0.5
            if std > 20:
                issues.append(f"High rubric dispersion: std={std:.1f} > 20")

        passed = len(issues) == 0
        suggestion = (
            None if passed
            else "Re-evaluate the submission with attention to the inconsistencies "
                 "listed above. Focus especially on aligning rubric dimension scores "
                 "with actual KP evidence."
        )
        return passed, issues, suggestion