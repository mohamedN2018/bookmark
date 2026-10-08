from django.core.management.base import BaseCommand
from books.models import Book, Author

class Command(BaseCommand):
    help = 'تحويل المؤلفين النصيين إلى نموذج Author'
    
    def handle(self, *args, **kwargs):
        # الحصول على جميع أسماء المؤلفين الفريدة
        books = Book.objects.all()
        author_names = set()
        
        for book in books:
            if book.author_name:
                author_names.add(book.author_name)
        
        # إنشاء مؤلفين جديدين
        created_count = 0
        for name in author_names:
            author, created = Author.objects.get_or_create(name=name)
            if created:
                created_count += 1
        
        # ربط الكتب بالمؤلفين
        for book in books:
            if book.author_name:
                author = Author.objects.get(name=book.author_name)
                book.author = author
                book.save()
        
        self.stdout.write(self.style.SUCCESS(f'تم إنشاء {created_count} مؤلف جديد'))