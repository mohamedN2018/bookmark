from django import forms
from django.contrib.auth.models import User
from .models import Review, Book
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError



class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="البريد الإلكتروني")
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'author_name',
            'category',
            'description',
            'cover_image',
            'pdf_file',
            'published_year',
            'pages',
            'language',
            'price',
            'is_free',
            'is_featured',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'title': forms.TextInput(attrs={'placeholder': 'أدخل عنوان الكتاب'}),
            'published_year': forms.NumberInput(attrs={'min': '1900', 'max': '2024'}),
            'pages': forms.NumberInput(attrs={'min': '1'}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        is_free = cleaned_data.get('is_free')
        price = cleaned_data.get('price')
        
        if is_free and price and float(price) > 0:
            raise forms.ValidationError('الكتب المجانية يجب أن يكون سعرها 0 ريال')
        
        if not is_free and price and float(price) <= 0:
            raise forms.ValidationError('الكتب المدفوعة يجب أن يكون سعرها أكبر من 0 ريال')
        
        return cleaned_data







class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="البريد الإلكتروني",
        widget=forms.EmailInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500',
            'placeholder': 'example@email.com'
        })
    )
    username = forms.CharField(
        label="اسم المستخدم",
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500',
            'placeholder': 'اختر اسم مستخدم فريد'
        })
    )
    password1 = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500',
            'placeholder': 'كلمة مرور قوية'
        })
    )
    password2 = forms.CharField(
        label="تأكيد كلمة المرور",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500',
            'placeholder': 'أعد إدخال كلمة المرور'
        })
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('هذا البريد الإلكتروني مستخدم بالفعل.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('اسم المستخدم هذا مستخدم بالفعل.')
        return username

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="اسم المستخدم أو البريد الإلكتروني",
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500',
            'placeholder': 'اسم المستخدم أو البريد الإلكتروني'
        })
    )
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500',
            'placeholder': 'كلمة المرور'
        })
    )