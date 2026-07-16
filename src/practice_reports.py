"""
Progress trends and analysis report export helpers.
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from swing_score import score_analysis


# Keys pulled from each analysis for the Progress chart
TREND_METRICS = [
    {'key': 'score', 'label': 'Swing Score', 'source': 'score'},
    {'key': 'max_shoulder_turn', 'label': 'Shoulder Turn', 'cam': 2},
    {'key': 'max_hip_turn', 'label': 'Hip Turn', 'cam': 2},
    {'key': 'max_x_factor', 'label': 'X-Factor', 'cam': 2},
    {'key': 'tempo_ratio', 'label': 'Tempo', 'cam': 1},
    {'key': 'max_sway_right', 'label': 'Lateral Sway', 'cam': 1},
    {'key': 'max_head_sway_right', 'label': 'Head Sway', 'cam': 1},
]


def _cam_summary(analysis: Dict, cam: int) -> Dict:
    block = analysis.get('camera1' if cam == 1 else 'camera2') or {}
    return block.get('summary') or {}


def load_analysis_file(path: str) -> Optional[Dict]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def build_progress_series(analyses: List[Dict]) -> Dict[str, Any]:
    """
    Build chronological trend series from a list of analysis payloads.

    Each item in ``analyses`` should include at least:
      timestamp, date (optional), camera1/camera2 summaries
    """
    # Sort oldest → newest for charts
    items = sorted(analyses, key=lambda a: a.get('timestamp') or '')

    series = {m['key']: [] for m in TREND_METRICS}
    points = []

    for a in items:
        ts = a.get('timestamp')
        date = a.get('date')
        if not date and ts:
            try:
                date = datetime.strptime(ts, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M')
            except ValueError:
                date = ts

        scored = score_analysis(a)
        point = {
            'timestamp': ts,
            'date': date,
            'score': scored.get('score'),
            'grade': scored.get('grade'),
            'metrics': {},
        }

        for m in TREND_METRICS:
            if m['key'] == 'score':
                val = scored.get('score')
            else:
                val = _cam_summary(a, m['cam']).get(m['key'])
            series[m['key']].append(val)
            point['metrics'][m['key']] = val

        points.append(point)

    # Summary deltas (first → last for scored swings)
    scored_pts = [p for p in points if p['score'] is not None]
    delta = None
    if len(scored_pts) >= 2:
        delta = round(scored_pts[-1]['score'] - scored_pts[0]['score'], 1)

    return {
        'count': len(points),
        'metrics': TREND_METRICS,
        'points': points,
        'series': series,
        'score_delta': delta,
        'latest_score': scored_pts[-1]['score'] if scored_pts else None,
        'latest_grade': scored_pts[-1]['grade'] if scored_pts else None,
    }


def analysis_to_csv(analysis: Dict, scored: Optional[Dict] = None) -> str:
    """Flat CSV of summary metrics + score breakdown."""
    if scored is None:
        scored = score_analysis(analysis)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['section', 'key', 'label', 'camera', 'value', 'rating', 'points'])
    writer.writerow(['score', 'score', 'Swing Score', '', scored.get('score'),
                     scored.get('grade'), ''])
    for e in scored.get('breakdown') or []:
        writer.writerow([
            'metric', e.get('key'), e.get('label'), e.get('cam'),
            e.get('value'), e.get('rating'), e.get('points'),
        ])
    # Raw summaries
    for cam_name, cam_num in (('camera1', 1), ('camera2', 2)):
        summary = _cam_summary(analysis, cam_num)
        for k, v in summary.items():
            writer.writerow(['summary', k, k, cam_num, v, '', ''])
    return buf.getvalue()


def analysis_to_html_report(analysis: Dict, scored: Optional[Dict] = None,
                            title: str = 'Golf Swing Analysis Report') -> str:
    """Self-contained HTML report for download / print."""
    if scored is None:
        scored = score_analysis(analysis)
    ts = analysis.get('timestamp') or ''
    try:
        date = datetime.strptime(ts, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        date = ts or 'Unknown'

    grade = scored.get('grade') or '—'
    score = scored.get('score')
    score_txt = f'{score:.1f}' if score is not None else '—'

    rows = []
    for e in scored.get('breakdown') or []:
        val = e.get('value')
        val_txt = '—' if val is None else (f'{val:.1f}' if isinstance(val, float) else str(val))
        rating = e.get('rating') or '—'
        color = {
            'good': '#238636', 'ok': '#9e6a03', 'needs_work': '#da3633'
        }.get(rating, '#8b949e')
        rows.append(
            f"<tr><td>{e.get('label')}</td><td>Cam {e.get('cam')}</td>"
            f"<td>{val_txt}</td>"
            f"<td style='color:{color};font-weight:600'>{rating}</td>"
            f"<td>{e.get('points') if e.get('points') is not None else '—'}</td></tr>"
        )

    strengths = ', '.join(scored.get('strengths') or []) or '—'
    focus = ', '.join(scored.get('focus_areas') or []) or '—'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1f2328; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .meta {{ color: #656d76; margin-bottom: 24px; }}
  .score-box {{ display: flex; gap: 24px; align-items: center; margin: 20px 0 28px;
                padding: 16px 20px; background: #f6f8fa; border-radius: 8px; }}
  .grade {{ font-size: 48px; font-weight: 700; line-height: 1; }}
  .score-num {{ font-size: 28px; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #d0d7de; font-size: 14px; }}
  th {{ background: #f6f8fa; }}
  .callout {{ margin-top: 20px; font-size: 14px; }}
  .callout strong {{ display: inline-block; min-width: 100px; }}
  @media print {{ body {{ margin: 0; }} }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">Recording: {date} &middot; ID: {ts}</div>
  <div class="score-box">
    <div class="grade">{grade}</div>
    <div>
      <div class="score-num">{score_txt} / 100</div>
      <div style="color:#656d76;font-size:13px">
        Rated {scored.get('rated_count', 0)} of {scored.get('metric_count', 0)} metrics
      </div>
    </div>
  </div>
  <div class="callout"><strong>Strengths:</strong> {strengths}</div>
  <div class="callout"><strong>Focus on:</strong> {focus}</div>
  <h2 style="font-size:16px;margin-top:28px">Metric breakdown</h2>
  <table>
    <thead><tr><th>Metric</th><th>Camera</th><th>Value</th><th>Rating</th><th>Points</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <p style="margin-top:32px;color:#656d76;font-size:12px">
    Generated by camera_recorder &middot; {datetime.now().strftime('%Y-%m-%d %H:%M')}
  </p>
</body>
</html>
"""
