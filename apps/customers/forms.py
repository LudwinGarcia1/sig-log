from django import forms

from apps.customers.models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "code", "business_name", "tax_id", "contact_name", "phone", "email",
            "address", "city", "state", "postal_code", "customer_type",
        ]
        widgets = {
            field: forms.TextInput(attrs={"class": "form-control"})
            for field in ["code", "business_name", "tax_id", "contact_name",
                          "phone", "address", "city", "state", "postal_code"]
        }
        widgets["email"] = forms.EmailInput(attrs={"class": "form-control"})
        widgets["customer_type"] = forms.Select(attrs={"class": "form-select"})

    def clean_tax_id(self):
        return self.cleaned_data["tax_id"].strip().upper()

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()
