from .dashboard_template_routes import register_dashboard_template_routes
from .demo_routes import register_demo_routes
from .notification_routes import register_notification_routes
from .reporting_routes import register_reporting_routes
from .logical_framework_routes import (
    LogicalFrameworkRouteDependencies,
    register_logical_framework_routes,
)

__all__ = [
    "register_dashboard_template_routes",
    "register_demo_routes",
    "register_notification_routes",
    "register_reporting_routes",
    "LogicalFrameworkRouteDependencies",
    "register_logical_framework_routes",
]
