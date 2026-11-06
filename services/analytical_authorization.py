"""Existing capability requirements shared by BI reads and executive projections.

An executive summary is permitted independently of detailed source rows. Never
use a role name to bypass these checks. Callers must establish tenant scope first.
"""

CAPABILITIES = {
    'summary': ('VIEW_EXECUTIVE_SNAPSHOT',),
    'indicators': ('VIEW_INDICATORS', 'VIEW_REPORTS'),
    'reporting': ('VIEW_REPORTS',),
    'workplan': ('VIEW_WORKPLAN',),
    'notifications': ('VIEW_NOTIFICATIONS',),
    'audit': ('VIEW_AUDIT_LOG',),
}
PROJECT_DASHBOARD_PERMISSIONS = tuple(dict.fromkeys(
    permission for category in ('summary', 'indicators', 'reporting', 'workplan', 'notifications')
    for permission in CAPABILITIES[category]))


def allows_category(permissions, category):
    """Use the same capability requirements in projections and their consumers."""
    return set(CAPABILITIES[category]) <= frozenset(permissions)


def project_snapshot_for_permissions(snapshot, permissions):
    """Preserve authorized sections, including null/zero and provenance, verbatim.

Restricted lists/objects keep their shape; restricted_sections distinguishes
redaction from genuine absence. Fully authorized responses have no added fields.
"""
    granted = frozenset(permissions)
    allowed = {category: allows_category(granted, category) for category in CAPABILITIES}
    if not allowed['summary']:
        # Defense in depth for reuse; the API gate normally rejects first.
        from .errors import ServiceError
        raise ServiceError(403, 'Missing required permission: VIEW_EXECUTIVE_SNAPSHOT.')
    result = dict(snapshot)
    restricted = []
    sections = {
        'indicators': ('indicators',),
        'reporting': ('trend', 'districts', 'reporting_records'),
        'workplan': ('activities', 'tasks', 'overdue_tasks', 'workflow'),
        'notifications': ('notifications',),
    }
    for category, fields in sections.items():
        if not allowed[category]:
            for field in fields:
                result[field] = {} if field == 'workflow' else []
                restricted.append(field)

    if not allowed['audit']:
        # This mixed feed contains ordinary operational history as well as audit
        # records. Keep only known event types covered by a category grant.
        event_categories = {
            'demo.task.created': 'workplan', 'demo.task.updated': 'workplan',
            'demo.task.started': 'workplan', 'demo.task.completed': 'workplan',
            'demo.task.submitted': 'workplan', 'demo.task.validated': 'workplan',
            'demo.task.approved': 'workplan', 'demo.task.returned': 'workplan',
            'demo.task.escalated': 'workplan', 'demo.task.routing_updated': 'workplan',
            'workflow.validation_backlog': 'workplan', 'workflow.overdue': 'workplan',
            'reporting_records.imported': 'reporting',
            'notification_rule.run_due': 'notifications', 'demo.notifications.simulated': 'notifications',
        }
        result['activity_feed'] = [item for item in snapshot['activity_feed']
                                   if allowed.get(event_categories.get(item.get('action')), False)]
        restricted.append('activity_feed.audit')

    details_allowed = set(PROJECT_DASHBOARD_PERMISSIONS) <= granted
    if not details_allowed:
        # Do not copy arbitrary nested narrative fields: they can contain source
        # notifications, reporting series, or future operational details.
        executive = result['executive']
        result['narrative'] = {
            'project_id': result['project']['project_id'],
            'project_name': result['project']['project_name'],
            'summary': (f"{result['project']['project_name']}: indicator-derived delivery health is NOT_ASSESSED. "
                        f"There are {executive.get('tasks_overdue', 0)} overdue task(s) and "
                        f"{executive.get('pending_validation_count', 0)} validation checkpoint(s)."),
            'insights': ['Indicator aggregation requires an approved comparable-group estimand.'],
            'recommended_actions': ['Review the authorized summary and follow up with the responsible team.'],
            'trend': result['trend'],
            'notifications': result['notifications'][:10],
        }
        restricted.append('narrative.details')

    dashboard = dict(snapshot['dashboard'])
    if not allowed['reporting']:
        # Custom template labels/configuration themselves require VIEW_REPORTS.
        # Retain a useful summary without exposing their text or detailed charts.
        executive = result['executive']
        dashboard = {'selected_template': {}, 'available_templates': [], 'widgets': [{
            'widget_id': 'executive-summary', 'title': 'Executive summary', 'chart_type': 'kpi_cards',
            'column_span': 2, 'row_span': 1, 'section': 'summary', 'content': {'cards': [
                {'label': 'Budget tracked', 'value': executive.get('budget_total'), 'prefix': '$'},
                {'label': 'Overdue tasks', 'value': executive.get('tasks_overdue')},
                {'label': 'Active alerts', 'value': executive.get('active_notifications')},
            ]},
        }]}
        restricted.extend(['dashboard.templates', 'dashboard.widgets'])
    elif not details_allowed:
        widgets = []
        summary_charts = {'kpi_cards', 'bullet_or_gauge', 'project_status_summary', 'budget_vs_actual'}
        chart_categories = {
            'line_trend': 'reporting', 'area_trend': 'reporting', 'map_placeholder': 'reporting',
            'status_donut': 'indicators', 'activity_progress': 'workplan',
            'notification_summary': 'notifications',
            # These widgets use district rows, falling back to indicator rows.
            'bar_comparison': 'reporting' if snapshot['districts'] else 'indicators',
            'variance_bar': 'reporting' if snapshot['districts'] else 'indicators',
        }
        for widget in dashboard['widgets']:
            kind = widget['chart_type']
            if kind == 'narrative_panel':
                widgets.append({**widget, 'content': {
                    'summary': result['narrative']['summary'], 'insights': result['narrative']['insights'][:5]}})
            elif kind in summary_charts or allowed.get(chart_categories.get(kind), False):
                widgets.append(widget)
            # Unknown chart types cannot implicitly inherit access.
        dashboard['widgets'] = widgets
        restricted.append('dashboard.widgets')
    result['dashboard'] = dashboard
    if restricted:
        result['restricted_sections'] = restricted
    return result
