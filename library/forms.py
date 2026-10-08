from django import forms

from .models import Rating


class RatingForm(forms.ModelForm):
    score = forms.TypedChoiceField(
        label="تقييمك", choices=[(i, str(i)) for i in range(5, 0, -1)], coerce=int, widget=forms.RadioSelect
    )

    class Meta:
        model = Rating
        fields = ["score", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "maxlength": 2000})}
