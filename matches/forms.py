from django import forms
from django.contrib.auth.models import User
from .models import GamedayJob, GamedayStaffAssignment


class UsernameChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


class GamedayJobForm(forms.ModelForm):
        class Meta:
            model = GamedayJob
            fields = ['job_name', 'location', 'staff_needed']
            widgets = {
                'job_name': forms.TextInput(attrs={'class': 'form-control'}),
                'location': forms.TextInput(attrs={'class': 'form-control'}),
                'staff_needed': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            }


class GamedayStaffAssignmentForm(forms.ModelForm):
        class Meta:
            model = GamedayStaffAssignment
            fields = ['person_name', 'contact_info', 'notes']
            widgets = {
                'person_name': forms.TextInput(attrs={'class': 'form-control'}),
                'contact_info': forms.TextInput(attrs={'class': 'form-control'}),
                'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
            }


class GamedayJobForm(forms.ModelForm):
    class Meta:
        model = GamedayJob
        fields = ['job_name', 'location', 'staff_needed']
        widgets = {
            'job_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Ticket Sales'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Main Entrance'}),
            'staff_needed': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class GamedayStaffAssignmentForm(forms.ModelForm):
    class Meta:
        model = GamedayStaffAssignment
        fields = ['person_name', 'contact_info', 'notes']
        widgets = {
            'person_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name',
                'list': 'staff-suggestions'
            }),
            'contact_info': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone or Email (Optional)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Any additional information about this assignment',
                'rows': 2
            }),
        }


class QuickAssignmentForm(forms.Form):
    """Form for quick multiple staff assignments"""
    staff_list = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter one name per line, or Name: Contact Info'
        }),
        help_text="Enter one person per line. You can optionally add contact info after a colon (Name: Contact)."
    )

    def clean_staff_list(self):
        data = self.cleaned_data['staff_list']
        staff = []

        for line in data.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            if ':' in line:
                name, contact = line.split(':', 1)
                staff.append({
                    'name': name.strip(),
                    'contact': contact.strip()
                })
            else:
                staff.append({
                    'name': line,
                    'contact': ''
                })

        if not staff:
            raise forms.ValidationError("Please enter at least one staff member.")

        return staff