"""
core/urls.py

URL patterns for: Dashboard (role-dispatched), global search,
                  system stats (admin).
Namespace: core
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [

    # ------------------------------------------------------------------
    # Dashboard — dispatches to role-specific view automatically
    # ------------------------------------------------------------------
    path('',
         views.dashboard_view,
         name='dashboard'),

    # ------------------------------------------------------------------
    # Global Search
    # ------------------------------------------------------------------
    path('search/',
         views.search_view,
         name='search'),

    # ------------------------------------------------------------------
    # System Stats (admin only)
    # ------------------------------------------------------------------
    path('system-stats/',
         views.system_stats_view,
         name='system_stats'),
]