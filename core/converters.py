class UnicodeSlugConverter:
    """مثل <slug:> لكن يقبل الحروف العربية (slugify(allow_unicode=True))."""

    regex = r"[-\w]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value
