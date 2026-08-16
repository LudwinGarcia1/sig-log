from django import forms

from apps.operators.models import Operator


class OperatorForm(forms.ModelForm):
    class Meta:
        model = Operator
        fields = [
            "employee_number", "first_name", "last_name", "license_number",
            "license_type", "license_expiry", "hire_date", "phone", "status",
        ]
        widgets = {
            "employee_number": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "license_number": forms.TextInput(attrs={"class": "form-control"}),
            "license_type": forms.Select(attrs={"class": "form-select"}),
            "license_expiry": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "hire_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        hire_date = cleaned.get("hire_date")
        expiry = cleaned.get("license_expiry")
        if hire_date and expiry and expiry < hire_date:
            raise forms.ValidationError(
                "La vigencia de la licencia no puede ser anterior al ingreso."
            )
        return cleaned
