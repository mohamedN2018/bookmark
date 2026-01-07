document.addEventListener('DOMContentLoaded', function() {
    // تهيئة GSAP
    gsap.registerPlugin(ScrollTrigger);
    
    // تأثيرات الخلفية
    initBackgroundAnimation();
    
    // تأثيرات الإحصائيات
    initStatistics();
    
    // تأثيرات النموذج
    initFormEffects();
    
    // تأثيرات الجدول
    initTableEffects();
    
    // تأثيرات البطاقات
    initCardEffects();
    
    // نظام Dark Mode
    initDarkMode();
    
    // نظام البحث والفلترة
    initSearchAndFilter();
    
    // نظام التصدير
    initExportSystem();
    
    // نظام الحذف والتعديل
    initCRUDActions();
    
    // تأثيرات متفرقة
    initMiscEffects();
});

// وظائف JavaScript المختلفة
function initBackgroundAnimation() {
    // حركة الدوائر في الخلفية
    gsap.to('.circle-1', {
        duration: 25,
        x: 200,
        y: 100,
        rotation: 360,
        ease: "none",
        repeat: -1,
        yoyo: true
    });
    
    gsap.to('.circle-2', {
        duration: 30,
        x: -150,
        y: -80,
        rotation: -360,
        ease: "none",
        repeat: -1,
        yoyo: true
    });
    
    gsap.to('.circle-3', {
        duration: 35,
        x: 120,
        y: -120,
        rotation: 180,
        ease: "none",
        repeat: -1,
        yoyo: true
    });
}

function initStatistics() {
    // تأثير عدادات الإحصائيات
    const counters = document.querySelectorAll('.counter');
    counters.forEach(counter => {
        const target = parseInt(counter.closest('.stat-card').dataset.count);
        const duration = 2000;
        const step = target / (duration / 16);
        let current = 0;
        
        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            counter.textContent = Math.floor(current);
        }, 16);
        
        // تأثير GSAP على البطاقة
        gsap.from(counter.closest('.stat-card'), {
            y: 50,
            opacity: 0,
            duration: 1,
            scrollTrigger: {
                trigger: counter.closest('.stat-card'),
                start: "top 80%"
            }
        });
    });
}

function initFormEffects() {
    // تأثيرات حقول النموذج
    const formInputs = document.querySelectorAll('#book-form input, #book-form select, #book-form textarea');
    
    formInputs.forEach(input => {
        // تأثير التركيز
        input.addEventListener('focus', function() {
            const formGroup = this.closest('.form-group');
            formGroup.classList.add('focused');
            
            gsap.to(this, {
                scale: 1.02,
                duration: 0.3,
                ease: "power2.out"
            });
        });
        
        input.addEventListener('blur', function() {
            const formGroup = this.closest('.form-group');
            formGroup.classList.remove('focused');
            
            gsap.to(this, {
                scale: 1,
                duration: 0.3,
                ease: "power2.out"
            });
        });
    });
    
    // تأثير رفع الصور
    const uploadArea = document.getElementById('cover-upload-area');
    const fileInput = uploadArea.querySelector('input[type="file"]');
    const previewContainer = document.getElementById('cover-preview');
    const previewImg = document.getElementById('cover-preview-img');
    
    if (uploadArea && fileInput) {
        // Drag and Drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            uploadArea.classList.add('dragover');
        }
        
        function unhighlight() {
            uploadArea.classList.remove('dragover');
        }
        
        // عرض الصورة المرفوعة
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImg.src = e.target.result;
                    previewContainer.classList.remove('hidden');
                    uploadArea.classList.add('hidden');
                    
                    // تأثير GSAP
                    gsap.from(previewContainer, {
                        scale: 0.8,
                        opacity: 0,
                        duration: 0.5,
                        ease: "back.out(1.2)"
                    });
                };
                reader.readAsDataURL(file);
            }
        });
        
        // إزالة الصورة
        const removeBtn = previewContainer?.querySelector('.remove-image-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', function() {
                fileInput.value = '';
                previewContainer.classList.add('hidden');
                uploadArea.classList.remove('hidden');
            });
        }
    }
    
    // عداد الأحرف
    const descriptionField = document.querySelector('#book-form textarea');
    const charCounter = document.querySelector('.character-counter');
    
    if (descriptionField && charCounter) {
        const maxCount = parseInt(charCounter.dataset.max);
        const currentSpan = charCounter.querySelector('.current-count');
        const maxSpan = charCounter.querySelector('.max-count');
        
        descriptionField.addEventListener('input', function() {
            const count = this.value.length;
            currentSpan.textContent = count;
            
            if (count > maxCount * 0.8) {
                charCounter.style.color = '#ef4444';
            } else {
                charCounter.style.color = '#6b7280';
            }
        });
    }
}

function initTableEffects() {
    // تأثيرات الصفوف
    const tableRows = document.querySelectorAll('.table-row');
    
    tableRows.forEach((row, index) => {
        // تأثير الظهور
        gsap.from(row, {
            opacity: 0,
            x: -30,
            duration: 0.6,
            delay: index * 0.05,
            scrollTrigger: {
                trigger: row,
                start: "top 90%"
            }
        });
        
        // تأثير Hover
        row.addEventListener('mouseenter', function() {
            gsap.to(this, {
                backgroundColor: '#f9fafb',
                duration: 0.2,
                ease: "power2.out"
            });
        });
        
        row.addEventListener('mouseleave', function() {
            gsap.to(this, {
                backgroundColor: '#ffffff',
                duration: 0.2,
                ease: "power2.out"
            });
        });
    });
}

function initCardEffects() {
    // تأثيرات البطاقات في العرض الشبكي
    const bookCards = document.querySelectorAll('.book-card');
    
    bookCards.forEach((card, index) => {
        // تأثير الظهور
        gsap.from(card, {
            opacity: 0,
            y: 30,
            scale: 0.9,
            duration: 0.6,
            delay: index * 0.1,
            scrollTrigger: {
                trigger: card,
                start: "top 85%"
            }
        });
        
        // تأثير Hover
        card.addEventListener('mouseenter', function() {
            gsap.to(this, {
                y: -10,
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                duration: 0.3,
                ease: "power2.out"
            });
        });
        
        card.addEventListener('mouseleave', function() {
            gsap.to(this, {
                y: 0,
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                duration: 0.3,
                ease: "power2.out"
            });
        });
    });
}

function initDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const darkModeIcon = document.getElementById('darkModeIcon');
    const htmlElement = document.documentElement;
    
    if (darkModeToggle && darkModeIcon) {
        // التحقق من التفضيل المحفوظ
        if (localStorage.getItem('darkMode') === 'true') {
            htmlElement.classList.add('dark');
            darkModeIcon.classList.remove('fa-moon');
            darkModeIcon.classList.add('fa-sun');
        }
        
        // تبديل Dark Mode
        darkModeToggle.addEventListener('click', function() {
            htmlElement.classList.toggle('dark');
            
            // تأثير GSAP
            gsap.fromTo(this,
                { scale: 1 },
                {
                    scale: 1.2,
                    duration: 0.2,
                    yoyo: true,
                    repeat: 1
                }
            );
            
            // تغيير الأيقونة
            if (htmlElement.classList.contains('dark')) {
                darkModeIcon.classList.remove('fa-moon');
                darkModeIcon.classList.add('fa-sun');
                localStorage.setItem('darkMode', 'true');
            } else {
                darkModeIcon.classList.remove('fa-sun');
                darkModeIcon.classList.add('fa-moon');
                localStorage.setItem('darkMode', 'false');
            }
        });
    }
}

function initSearchAndFilter() {
    // زر الفلاتر
    const filterBtn = document.querySelector('.filter-btn');
    const advancedFilters = document.getElementById('advanced-filters');
    
    if (filterBtn && advancedFilters) {
        filterBtn.addEventListener('click', function() {
            advancedFilters.classList.toggle('hidden');
            
            // تأثير GSAP
            if (advancedFilters.classList.contains('hidden')) {
                gsap.to(advancedFilters, {
                    height: 0,
                    opacity: 0,
                    duration: 0.3,
                    ease: "power2.out"
                });
            } else {
                advancedFilters.style.height = 'auto';
                gsap.from(advancedFilters, {
                    height: 0,
                    opacity: 0,
                    duration: 0.3,
                    ease: "power2.out"
                });
            }
            
            // تأثير على زر الفلاتر
            gsap.fromTo(this,
                { scale: 1 },
                {
                    scale: 1.1,
                    duration: 0.2,
                    yoyo: true,
                    repeat: 1
                }
            );
        });
    }
    
    // تبديل طريقة العرض
    const viewModeBtns = document.querySelectorAll('.view-mode-btn');
    const tableView = document.getElementById('table-view');
    const gridView = document.getElementById('grid-view');
    
    viewModeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.dataset.view;
            
            // تحديث الأزرار النشطة
            viewModeBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // تبديل العرض
            if (view === 'table') {
                tableView.classList.add('active');
                tableView.classList.remove('hidden');
                gridView.classList.remove('active');
                gridView.classList.add('hidden');
                
                // تأثير GSAP
                gsap.from(tableView, {
                    opacity: 0,
                    x: -20,
                    duration: 0.4,
                    ease: "power2.out"
                });
            } else {
                gridView.classList.add('active');
                gridView.classList.remove('hidden');
                tableView.classList.remove('active');
                tableView.classList.add('hidden');
                
                // تأثير GSAP
                gsap.from(gridView, {
                    opacity: 0,
                    y: 20,
                    duration: 0.4,
                    ease: "power2.out"
                });
            }
        });
    });
}

function initExportSystem() {
    // أزرار التصدير
    const exportBtns = document.querySelectorAll('.export-btn');
    
    exportBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const format = this.dataset.format;
            
            // محاكاة التصدير
            showToast(`جاري تصدير البيانات بصيغة ${format.toUpperCase()}...`, 'success');
            
            // تأثير GSAP
            gsap.fromTo(this,
                { scale: 1 },
                {
                    scale: 0.9,
                    duration: 0.1,
                    yoyo: true,
                    repeat: 1
                }
            );
        });
    });
}

function initCRUDActions() {
    // أزرار الحذف
    const deleteBtns = document.querySelectorAll('.delete-btn');
    const deleteModal = document.getElementById('delete-modal');
    const deleteMessage = document.getElementById('delete-message');
    const cancelDelete = document.getElementById('cancel-delete');
    const confirmDelete = document.getElementById('confirm-delete');
    
    let currentBookId = null;
    let currentBookTitle = null;
    
    deleteBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            currentBookId = this.dataset.bookId;
            currentBookTitle = this.dataset.bookTitle;
            
            // تحديث رسالة التأكيد
            deleteMessage.textContent = `هل أنت متأكد من رغبتك في حذف الكتاب "${currentBookTitle}"؟`;
            
            // إظهار الـ Modal
            showModal(deleteModal);
        });
    });
    
    // إغلاق الـ Modal
    if (cancelDelete) {
        cancelDelete.addEventListener('click', function() {
            hideModal(deleteModal);
        });
    }
    
    // تأكيد الحذف
    if (confirmDelete) {
        confirmDelete.addEventListener('click', function() {
            if (!currentBookId) return;
            
            // إرسال طلب AJAX للحذف
            deleteBook(currentBookId, currentBookTitle);
            hideModal(deleteModal);
        });
    }
    
    // أزرار التعديل
    const editBtns = document.querySelectorAll('.edit-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const formTitle = document.getElementById('form-title');
    const submitFormBtn = document.getElementById('submit-form-btn');
    const btnText = submitFormBtn.querySelector('.btn-text');
    const btnIcon = submitFormBtn.querySelector('.btn-icon i');
    
    editBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const bookId = this.dataset.bookId;
            
            // تغيير النموذج لوضع التعديل
            formTitle.textContent = 'تعديل الكتاب';
            btnText.textContent = 'تحديث الكتاب';
            btnIcon.classList.remove('fa-plus');
            btnIcon.classList.add('fa-save');
            cancelEditBtn.style.display = 'inline-block';
            
            // تحميل بيانات الكتاب
            loadBookData(bookId);
            
            // تمرير إلى أعلى الصفحة
            document.getElementById('book-form-container').scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
    
    // إلغاء التعديل
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', function() {
            resetForm();
        });
    }
}

function initMiscEffects() {
    // تأثيرات الأزرار السريعة
    const controlBtns = document.querySelectorAll('.control-btn');
    
    controlBtns.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            gsap.to(this, {
                y: -3,
                duration: 0.2,
                ease: "power2.out"
            });
        });
        
        btn.addEventListener('mouseleave', function() {
            gsap.to(this, {
                y: 0,
                duration: 0.2,
                ease: "power2.out"
            });
        });
    });
    
    // تأثيرات الأزرار الفارغة
    const emptyStateBtns = document.querySelectorAll('.empty-state-btn');
    
    emptyStateBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            document.getElementById('quick-add-btn').click();
        });
    });
}

// وظائف مساعدة
function showModal(modal) {
    modal.classList.remove('hidden');
    
    gsap.fromTo(modal.querySelector('.modal-overlay'),
        { opacity: 0 },
        { opacity: 1, duration: 0.3 }
    );
    
    gsap.fromTo(modal.querySelector('.modal-content'),
        { scale: 0.8, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.4, ease: "back.out(1.2)" }
    );
}

function hideModal(modal) {
    gsap.to(modal.querySelector('.modal-content'), {
        scale: 0.8,
        opacity: 0,
        duration: 0.3,
        ease: "power2.in",
        onComplete: () => {
            modal.classList.add('hidden');
        }
    });
    
    gsap.to(modal.querySelector('.modal-overlay'), {
        opacity: 0,
        duration: 0.3
    });
}

function showToast(message, type = 'success') {
    const toastContainer = type === 'success' ? 
        document.getElementById('success-toast') : 
        document.getElementById('error-toast');
    
    const toastMessage = toastContainer.querySelector('.toast-text');
    toastMessage.textContent = message;
    
    toastContainer.classList.remove('hidden');
    
    // إغلاق تلقائي بعد 3 ثواني
    setTimeout(() => {
        toastContainer.classList.add('hidden');
    }, 3000);
}

function deleteBook(bookId, bookTitle) {
    // محاكاة حذف الكتاب
    fetch(`/dashboard/books/${bookId}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('تم حذف الكتاب بنجاح', 'success');
            
            // إزالة العنصر من الواجهة
            const bookElement = document.querySelector(`[data-book-id="${bookId}"]`);
            if (bookElement) {
                gsap.to(bookElement, {
                    opacity: 0,
                    x: -30,
                    height: 0,
                    margin: 0,
                    padding: 0,
                    duration: 0.4,
                    ease: "power2.in",
                    onComplete: () => {
                        bookElement.remove();
                    }
                });
            }
        } else {
            showToast(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('حدث خطأ أثناء حذف الكتاب', 'error');
    });
}

function loadBookData(bookId) {
    // محاكاة تحميل بيانات الكتاب
    fetch(`/dashboard/books/${bookId}/data/`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // تعبئة الحقول ببيانات الكتاب
            Object.keys(data.book).forEach(key => {
                const field = document.querySelector(`[name="${key}"]`);
                if (field) {
                    field.value = data.book[key];
                }
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('حدث خطأ أثناء تحميل بيانات الكتاب', 'error');
    });
}

function resetForm() {
    const form = document.getElementById('book-form');
    const formTitle = document.getElementById('form-title');
    const submitFormBtn = document.getElementById('submit-form-btn');
    const btnText = submitFormBtn.querySelector('.btn-text');
    const btnIcon = submitFormBtn.querySelector('.btn-icon i');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    
    form.reset();
    formTitle.textContent = 'إضافة كتاب جديد';
    btnText.textContent = 'إضافة الكتاب';
    btnIcon.classList.remove('fa-save');
    btnIcon.classList.add('fa-plus');
    cancelEditBtn.style.display = 'none';
    
    // إعادة تعيين معاينة الصورة
    const previewContainer = document.getElementById('cover-preview');
    const uploadArea = document.getElementById('cover-upload-area');
    if (previewContainer && uploadArea) {
        previewContainer.classList.add('hidden');
        uploadArea.classList.remove('hidden');
    }
}

function getCSRFToken() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfToken ? csrfToken.value : '';
}