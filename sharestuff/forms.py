from django import forms
from django.contrib.admin.widgets import AdminTimeWidget
import djangoforms
from models import User

SEARCH_CHOICES = (
    ('byname', 'by name'),
    ('bytime', 'by time'),
)

class RegisterForm(djangoforms.ModelForm):
    email = forms.CharField(max_length=128)
    password = forms.CharField(widget=forms.PasswordInput)
    name = forms.CharField(max_length=128)
    class Meta:
        model = User

class LoginForm(forms.Form):
    email = forms.CharField(label="email", max_length=128)
    password = forms.CharField(label="password:",widget=forms.PasswordInput)

class ResourceForm(forms.Form):
    resource_id = forms.CharField(widget=forms.HiddenInput)
    name = forms.CharField(max_length=128)
    description = forms.CharField(max_length=1024, required=False)
    tags = forms.CharField(max_length=128)
    starttime = forms.TimeField(input_formats=('%I:%M %p',))
    endtime = forms.TimeField(input_formats=('%I:%M %p', ))
    image = forms.FileField(required=False)

class ReserveForm(forms.Form):
    starttime = forms.TimeField(input_formats=('%I:%M %p',))
    duration = forms.IntegerField()
    user = forms.CharField(widget=forms.HiddenInput())
    resource_id = forms.CharField(widget=forms.HiddenInput())

class SearchForm(forms.Form):
    name = forms.CharField(max_length=128, required=False)
    time = forms.TimeField(input_formats=('%I:%M %p',), required=False)
    duration = forms.IntegerField(required=False)

