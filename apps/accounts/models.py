"""
accounts/models.py

Custom User model with role-based access control.
Extends AbstractBaseUser for full control over authentication.
Includes StudentProfile and ProfessorProfile for role-specific data.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.utils import timezone
from django.urls import reverse


# ---------------------------------------------------------------------------
# Role Constants
# ---------------------------------------------------------------------------
class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Administrator'
    PROFESSOR = 'professor', 'Professor'
    STUDENT = 'student', 'Student'


# ---------------------------------------------------------------------------
# Custom User Manager
# ---------------------------------------------------------------------------
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

    def get_admins(self):
        return self.filter(role=UserRole.ADMIN, is_active=True)

    def get_professors(self):
        return self.filter(role=UserRole.PROFESSOR, is_active=True)

    def get_students(self):
        return self.filter(role=UserRole.STUDENT, is_active=True)


# ---------------------------------------------------------------------------
# Custom User Model
# ---------------------------------------------------------------------------
class User(AbstractBaseUser, PermissionsMixin):
    """
    Central user model. Email is the unique identifier.
    Role determines dashboard access and permissions.
    """

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits."
    )

    # Core fields
    email = models.EmailField(unique=True, verbose_name='Email Address')
    first_name = models.CharField(max_length=100, verbose_name='First Name')
    last_name = models.CharField(max_length=100, verbose_name='Last Name')
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        verbose_name='Role'
    )

    # Contact
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name='Phone Number'
    )

    # Profile photo
    profile_photo = models.ImageField(
        upload_to='profile_photos/',
        blank=True,
        null=True,
        verbose_name='Profile Photo'
    )

    # Bio / address
    bio = models.TextField(blank=True, verbose_name='Biography')
    address = models.TextField(blank=True, verbose_name='Address')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='Date of Birth')

    # Status & Timestamps
    is_active = models.BooleanField(default=True, verbose_name='Active')
    is_staff = models.BooleanField(default=False, verbose_name='Staff Status')
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='Date Joined')
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='Last Login IP')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_role_display()})'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name

    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'pk': self.pk})

    # ------------------------------------------------------------------
    # Role helpers
    # ------------------------------------------------------------------
    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_professor(self):
        return self.role == UserRole.PROFESSOR

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def role_dashboard_url(self):
        return reverse('core:dashboard')

    @property
    def profile_photo_url(self):
        if self.profile_photo:
            return self.profile_photo.url
        return '/static/img/default_avatar.png'

    def get_initials(self):
        parts = [self.first_name[:1], self.last_name[:1]]
        return ''.join(parts).upper()


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------
class Department(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name='Department Name')
    code = models.CharField(max_length=10, unique=True, verbose_name='Code')
    description = models.TextField(blank=True, verbose_name='Description')
    head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments',
        limit_choices_to={'role': UserRole.PROFESSOR},
        verbose_name='Department Head'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments'
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']

    def __str__(self):
        return f'{self.code} — {self.name}'


# ---------------------------------------------------------------------------
# Student Profile
# ---------------------------------------------------------------------------
class StudentProfile(models.Model):

    YEAR_CHOICES = [
        (1, 'Freshman'),
        (2, 'Sophomore'),
        (3, 'Junior'),
        (4, 'Senior'),
        (5, 'Graduate'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('graduated', 'Graduated'),
        ('suspended', 'Suspended'),
        ('withdrawn', 'Withdrawn'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name='User'
    )
    student_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Student ID'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name='Department'
    )
    year_of_study = models.PositiveSmallIntegerField(
        choices=YEAR_CHOICES,
        default=1,
        verbose_name='Year of Study'
    )
    enrollment_date = models.DateField(default=timezone.now, verbose_name='Enrollment Date')
    expected_graduation = models.DateField(null=True, blank=True, verbose_name='Expected Graduation')
    gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        verbose_name='GPA'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Academic Status'
    )
    emergency_contact_name = models.CharField(max_length=200, blank=True, verbose_name='Emergency Contact Name')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, verbose_name='Emergency Contact Phone')
    scholarship = models.BooleanField(default=False, verbose_name='On Scholarship')
    notes = models.TextField(blank=True, verbose_name='Admin Notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_profiles'
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'
        ordering = ['student_id']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.student_id} — {self.user.get_full_name()}'

    def get_absolute_url(self):
        return reverse('accounts:student_detail', kwargs={'pk': self.pk})

    @property
    def year_label(self):
        return dict(self.YEAR_CHOICES).get(self.year_of_study, 'Unknown')

    def update_gpa(self):
        """Recalculate GPA from all finalized grades."""
        from apps.grades.models import Grade
        grades = Grade.objects.filter(
            enrollment__student=self,
            is_finalized=True
        )
        if not grades.exists():
            self.gpa = 0.00
        else:
            total_points = sum(g.grade_points for g in grades)
            self.gpa = round(total_points / grades.count(), 2)
        self.save(update_fields=['gpa'])


# ---------------------------------------------------------------------------
# Professor Profile
# ---------------------------------------------------------------------------
class ProfessorProfile(models.Model):

    RANK_CHOICES = [
        ('adjunct', 'Adjunct Professor'),
        ('assistant', 'Assistant Professor'),
        ('associate', 'Associate Professor'),
        ('full', 'Full Professor'),
        ('emeritus', 'Professor Emeritus'),
        ('lecturer', 'Lecturer'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='professor_profile',
        verbose_name='User'
    )
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Employee ID'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='professors',
        verbose_name='Department'
    )
    rank = models.CharField(
        max_length=20,
        choices=RANK_CHOICES,
        default='assistant',
        verbose_name='Academic Rank'
    )
    specialization = models.CharField(max_length=300, blank=True, verbose_name='Specialization')
    office_location = models.CharField(max_length=100, blank=True, verbose_name='Office Location')
    office_hours = models.TextField(blank=True, verbose_name='Office Hours')
    hire_date = models.DateField(default=timezone.now, verbose_name='Hire Date')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    website = models.URLField(blank=True, verbose_name='Personal Website')
    publications = models.TextField(blank=True, verbose_name='Publications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'professor_profiles'
        verbose_name = 'Professor Profile'
        verbose_name_plural = 'Professor Profiles'
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department']),
        ]

    def __str__(self):
        return f'{self.employee_id} — {self.user.get_full_name()} ({self.get_rank_display()})'

    def get_absolute_url(self):
        return reverse('accounts:professor_detail', kwargs={'pk': self.pk})

    @property
    def total_courses(self):
        return self.user.taught_courses.count()

    @property
    def active_courses(self):
        from apps.courses.models import Course
        return self.user.taught_courses.filter(is_active=True).count()