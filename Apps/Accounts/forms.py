"""
accounts/forms.py

Forms: Login, Registration, Profile editing, Password change,
       Student/Professor profile forms, Department form.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import User, UserRole, StudentProfile, ProfessorProfile, Department


# ---------------------------------------------------------------------------
# Shared widget style helper
# ---------------------------------------------------------------------------
def _fc(placeholder='', extra_class=''):
    """Return standard Bootstrap form-control attrs."""
    return {
        'class': f'form-control {extra_class}'.strip(),
        'placeholder': placeholder,
    }


def _fs(extra_class=''):
    return {'class': f'form-select {extra_class}'.strip()}


# ---------------------------------------------------------------------------
# Login Form
# ---------------------------------------------------------------------------
class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={**_fc('Enter your email'), 'autofocus': True})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs=_fc('Enter your password'))
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                'This account has been deactivated. Please contact the administrator.',
                code='inactive',
            )


# ---------------------------------------------------------------------------
# User Registration Form
# ---------------------------------------------------------------------------
class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs=_fc('Create a strong password')),
        min_length=8,
        help_text='At least 8 characters.'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs=_fc('Re-enter your password'))
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email',
            'role', 'phone', 'date_of_birth',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs=_fc('First name')),
            'last_name': forms.TextInput(attrs=_fc('Last name')),
            'email': forms.EmailInput(attrs=_fc('Email address')),
            'role': forms.Select(attrs=_fs()),
            'phone': forms.TextInput(attrs=_fc('+1234567890')),
            'date_of_birth': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError({'password2': 'Passwords do not match.'})
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


# ---------------------------------------------------------------------------
# User Edit Form (Admin editing any user)
# ---------------------------------------------------------------------------
class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'role',
            'phone', 'date_of_birth', 'bio', 'address',
            'profile_photo', 'is_active',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs=_fc('First name')),
            'last_name': forms.TextInput(attrs=_fc('Last name')),
            'email': forms.EmailInput(attrs=_fc('Email address')),
            'role': forms.Select(attrs=_fs()),
            'phone': forms.TextInput(attrs=_fc('+1234567890')),
            'date_of_birth': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
            'bio': forms.Textarea(attrs={**_fc('Short biography...'), 'rows': 3}),
            'address': forms.Textarea(attrs={**_fc('Full address...'), 'rows': 2}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('A user with this email already exists.')
        return email


# ---------------------------------------------------------------------------
# Profile Form (user editing their own profile)
# ---------------------------------------------------------------------------
class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone',
            'date_of_birth', 'bio', 'address', 'profile_photo',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs=_fc('First name')),
            'last_name': forms.TextInput(attrs=_fc('Last name')),
            'phone': forms.TextInput(attrs=_fc('+1234567890')),
            'date_of_birth': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
            'bio': forms.Textarea(attrs={**_fc('Tell us about yourself...'), 'rows': 4}),
            'address': forms.Textarea(attrs={**_fc('Your address...'), 'rows': 2}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


# ---------------------------------------------------------------------------
# Custom Password Change Form
# ---------------------------------------------------------------------------
class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs=_fc('Current password'))
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs=_fc('New password')),
        min_length=8
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs=_fc('Confirm new password'))
    )


# ---------------------------------------------------------------------------
# Student Profile Form
# ---------------------------------------------------------------------------
class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'student_id', 'department', 'year_of_study',
            'enrollment_date', 'expected_graduation',
            'status', 'emergency_contact_name',
            'emergency_contact_phone', 'scholarship', 'notes',
        ]
        widgets = {
            'student_id': forms.TextInput(attrs=_fc('e.g. STU-2025-001')),
            'department': forms.Select(attrs=_fs()),
            'year_of_study': forms.Select(attrs=_fs()),
            'enrollment_date': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
            'expected_graduation': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
            'status': forms.Select(attrs=_fs()),
            'emergency_contact_name': forms.TextInput(attrs=_fc('Contact name')),
            'emergency_contact_phone': forms.TextInput(attrs=_fc('+1234567890')),
            'scholarship': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={**_fc('Admin notes...'), 'rows': 3}),
        }

    def clean_student_id(self):
        sid = self.cleaned_data.get('student_id', '').strip().upper()
        qs = StudentProfile.objects.filter(student_id=sid)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('This Student ID is already in use.')
        return sid


# ---------------------------------------------------------------------------
# Professor Profile Form
# ---------------------------------------------------------------------------
class ProfessorProfileForm(forms.ModelForm):
    class Meta:
        model = ProfessorProfile
        fields = [
            'employee_id', 'department', 'rank',
            'specialization', 'office_location', 'office_hours',
            'hire_date', 'website', 'publications', 'is_active',
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs=_fc('e.g. EMP-2020-042')),
            'department': forms.Select(attrs=_fs()),
            'rank': forms.Select(attrs=_fs()),
            'specialization': forms.TextInput(attrs=_fc('Area of expertise')),
            'office_location': forms.TextInput(attrs=_fc('e.g. Building A, Room 302')),
            'office_hours': forms.Textarea(attrs={
                **_fc('e.g. Mon/Wed 2–4 PM, Fri 10 AM–12 PM'), 'rows': 2
            }),
            'hire_date': forms.DateInput(attrs={**_fc(), 'type': 'date'}),
            'website': forms.URLInput(attrs=_fc('https://')),
            'publications': forms.Textarea(attrs={
                **_fc('List publications here...'), 'rows': 4
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_employee_id(self):
        eid = self.cleaned_data.get('employee_id', '').strip().upper()
        qs = ProfessorProfile.objects.filter(employee_id=eid)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('This Employee ID is already in use.')
        return eid


# ---------------------------------------------------------------------------
# Department Form
# ---------------------------------------------------------------------------
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'head']
        widgets = {
            'name': forms.TextInput(attrs=_fc('Department name')),
            'code': forms.TextInput(attrs=_fc('e.g. CS, MATH, ENG')),
            'description': forms.Textarea(attrs={**_fc('Description...'), 'rows': 3}),
            'head': forms.Select(attrs=_fs()),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        qs = Department.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('A department with this code already exists.')
        return code