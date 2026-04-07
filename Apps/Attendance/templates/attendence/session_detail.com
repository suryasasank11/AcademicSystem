{% extends 'base.html' %}
{% block title %}Session — {{ session.date }}{% endblock %}
{% block breadcrumb %}
<li class="breadcrumb-item"><a href="{% url 'attendance:session_list' %}">Attendance</a></li>
<li class="breadcrumb-item active">{{ session.date }}</li>
{% endblock %}
{% block page_header %}
<div class="page-header">
  <h1 class="page-title">
    <i class="fas fa-calendar-day me-2"></i>
    {{ session.course.course_code }} — {{ session.date|date:"M d, Y" }}
  </h1>
  <div class="page-actions">
    {% if not session.is_locked %}
    <a href="{% url 'attendance:mark' session.pk %}" class="btn btn-primary">
      <i class="fas fa-edit me-1"></i>Edit Attendance
    </a>
    {% endif %}
    {% if request.user.is_admin or request.user.is_superuser %}
    <form method="post" action="{% url 'attendance:toggle_lock' session.pk %}" class="d-inline">
      {% csrf_token %}
      <button type="submit" class="btn {% if session.is_locked %}btn-outline-success{% else %}btn-outline-warning{% endif %}">
        <i class="fas fa-{% if session.is_locked %}unlock{% else %}lock{% endif %} me-1"></i>
        {% if session.is_locked %}Unlock{% else %}Lock{% endif %}
      </button>
    </form>
    {% endif %}
  </div>
</div>
{% endblock %}
{% block content %}

<!-- Stats Row -->
<div class="row g-3 mb-4">
  <div class="col-6 col-md-3">
    <div class="stat-card stat-card-success">
      <div class="stat-icon"><i class="fas fa-check-circle"></i></div>
      <div class="stat-value">{{ session.present_count }}</div>
      <div class="stat-label">Present</div>
    </div>
  </div>
  <div class="col-6 col-md-3">
    <div class="stat-card stat-card-danger">
      <div class="stat-icon"><i class="fas fa-times-circle"></i></div>
      <div class="stat-value">{{ session.absent_count }}</div>
      <div class="stat-label">Absent</div>
    </div>
  </div>
  <div class="col-6 col-md-3">
    <div class="stat-card stat-card-warning">
      <div class="stat-icon"><i class="fas fa-clock"></i></div>
      <div class="stat-value">{{ session.late_count }}</div>
      <div class="stat-label">Late</div>
    </div>
  </div>
  <div class="col-6 col-md-3">
    <div class="stat-card stat-card-info">
      <div class="stat-icon"><i class="fas fa-chart-pie"></i></div>
      <div class="stat-value">{{ session.attendance_rate }}%</div>
      <div class="stat-label">Rate</div>
    </div>
  </div>
</div>

<div class="row g-4">
  <!-- Session Info -->
  <div class="col-lg-3">
    <div class="card shadow-sm">
      <div class="card-header"><h6 class="mb-0">Session Info</h6></div>
      <div class="card-body">
        <table class="table table-sm table-borderless mb-0">
          <tr><td class="text-muted">Course</td><td><strong>{{ session.course.course_code }}</strong></td></tr>
          <tr><td class="text-muted">Date</td><td>{{ session.date }}</td></tr>
          <tr><td class="text-muted">Type</td><td>{{ session.get_session_type_display }}</td></tr>
          {% if session.topic %}<tr><td class="text-muted">Topic</td><td>{{ session.topic }}</td></tr>{% endif %}
          <tr><td class="text-muted">Created</td><td class="small">{{ session.created_by.get_full_name|default:"—" }}</td></tr>
          <tr>
            <td class="text-muted">Status</td>
            <td>{% if session.is_locked %}<span class="badge bg-secondary"><i class="fas fa-lock me-1"></i>Locked</span>{% else %}<span class="badge bg-success">Open</span>{% endif %}</td>
          </tr>
        </table>
        {% if session.notes %}
          <hr><p class="text-muted small mb-0">{{ session.notes }}</p>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- Attendance Records Table -->
  <div class="col-lg-9">
    <div class="card shadow-sm">
      <div class="card-header"><h6 class="mb-0"><i class="fas fa-list me-2"></i>Attendance Records ({{ session.total_students }} students)</h6></div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr><th>Student</th><th>ID</th><th>Status</th><th>Excuse / Note</th><th class="text-end">Action</th></tr>
            </thead>
            <tbody>
              {% for record in records %}
              <tr>
                <td class="fw-semibold">{{ record.enrollment.student.user.get_full_name }}</td>
                <td class="text-muted small">{{ record.enrollment.student.student_id }}</td>
                <td>
                  <span class="badge bg-{{ record.status_badge_class }}">
                    <i class="fas {{ record.status_icon }} me-1"></i>
                    {{ record.get_status_display }}
                  </span>
                </td>
                <td class="text-muted small">{{ record.excuse_reason|default:record.notes|default:"—"|truncatechars:40 }}</td>
                <td class="text-end">
                  {% if not session.is_locked %}
                  <a href="{% url 'attendance:update_record' record.pk %}" class="btn btn-xs btn-outline-secondary">
                    <i class="fas fa-edit"></i>
                  </a>
                  {% endif %}
                </td>
              </tr>
              {% empty %}
              <tr><td colspan="5" class="text-center text-muted py-4">No records found.</td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}