from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

INPUT_CLASS = "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="البريد الإلكتروني",
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "example@email.com"}),
    )
    username = forms.CharField(
        label="اسم المستخدم",
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "اختر اسم مستخدم فريد"}),
    )
    password1 = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "placeholder": "كلمة مرور قوية"}),
    )
    password2 = forms.CharField(
        label="تأكيد كلمة المرور",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "placeholder": "أعد إدخال كلمة المرور"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """تحديث بيانات الحساب. تغيير كلمة المرور يتطلب كلمة المرور الحالية."""

    email = forms.EmailField(required=True, label="البريد الإلكتروني")
    current_password = forms.CharField(required=False, widget=forms.PasswordInput, label="كلمة المرور الحالية")
    new_password = forms.CharField(required=False, widget=forms.PasswordInput, label="كلمة المرور الجديدة")
    new_password_confirm = forms.CharField(required=False, widget=forms.PasswordInput, label="تأكيد كلمة المرور")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")
        return email

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        if new:
            if not self.instance.check_password(cleaned.get("current_password") or ""):
                self.add_error("current_password", "كلمة المرور الحالية غير صحيحة.")
            if new != cleaned.get("new_password_confirm"):
                self.add_error("new_password_confirm", "كلمتا المرور غير متطابقتين.")
            try:
                password_validation.validate_password(new, self.instance)
            except ValidationError as exc:
                self.add_error("new_password", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])
        if commit:
            user.save()
        return user
