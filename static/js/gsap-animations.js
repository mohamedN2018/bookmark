// تهيئة تأثيرات GSAP المتقدمة
document.addEventListener('DOMContentLoaded', function() {
    // تأثيرات شريط التنقل عند التمرير
    const navbar = document.getElementById('navbar');
    let lastScroll = 0;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll <= 0) {
            navbar.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
            return;
        }
        
        if (currentScroll > lastScroll && currentScroll > 100) {
            // التمرير لأسفل
            gsap.to(navbar, {
                y: -100,
                duration: 0.3
            });
        } else if (currentScroll < lastScroll) {
            // التمرير لأعلى
            gsap.to(navbar, {
                y: 0,
                duration: 0.3
            });
            
            if (currentScroll > 50) {
                navbar.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
            }
        }
        
        lastScroll = currentScroll;
    });
    
    // تأثيرات على أزرار الحركة
    const actionButtons = document.querySelectorAll('.action-btn');
    actionButtons.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            gsap.to(this, {
                scale: 1.05,
                duration: 0.2
            });
        });
        
        btn.addEventListener('mouseleave', function() {
            gsap.to(this, {
                scale: 1,
                duration: 0.2
            });
        });
    });
    
    // تأثيرات على بطاقات الكتب عند المرور عليها
    const bookCards = document.querySelectorAll('.book-card');
    bookCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            gsap.to(this, {
                y: -10,
                duration: 0.3
            });
        });
        
        card.addEventListener('mouseleave', function() {
            gsap.to(this, {
                y: 0,
                duration: 0.3
            });
        });
    });
    
    // تأثيرات ظهور الصفحات
    const pageContent = document.querySelector('main');
    if (pageContent) {
        gsap.from(pageContent, {
            opacity: 0,
            y: 20,
            duration: 0.8,
            delay: 0.2
        });
    }
    
    // تأثيرات الرسائل
    const messages = document.querySelectorAll('.alert');
    messages.forEach(msg => {
        gsap.from(msg, {
            opacity: 0,
            y: -20,
            duration: 0.5
        });
        
        // إخفاء الرسائل بعد 5 ثواني
        setTimeout(() => {
            gsap.to(msg, {
                opacity: 0,
                y: -20,
                duration: 0.5,
                onComplete: () => {
                    msg.remove();
                }
            });
        }, 5000);
    });
});

// وظيفة لتحميل المحتوى الديناميكي
function loadContent(url, targetElement) {
    return fetch(url)
        .then(response => response.text())
        .then(html => {
            targetElement.innerHTML = html;
            
            // إطلاق حدث لتحديث الرسوم المتحركة
            document.dispatchEvent(new Event('contentChanged'));
            
            return html;
        })
        .catch(error => {
            console.error('Error loading content:', error);
            targetElement.innerHTML = '<p class="text-red-500">حدث خطأ في تحميل المحتوى</p>';
        });
}