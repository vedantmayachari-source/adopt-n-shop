// Adopt n Shop - Customer & Public JavaScript Interactivity

document.addEventListener('DOMContentLoaded', function () {
  // 1. Auto-dismiss flash alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 5000);
  });

  // 2. Quantity Selectors on Product Detail & Cart Pages
  const qtyInputs = document.querySelectorAll('.qty-input');
  qtyInputs.forEach(function (input) {
    const parent = input.closest('.qty-control-group');
    if (!parent) return;

    const btnMinus = parent.querySelector('.btn-qty-minus');
    const btnPlus = parent.querySelector('.btn-qty-plus');
    const maxStock = parseInt(input.getAttribute('max') || '999');

    if (btnMinus) {
      btnMinus.addEventListener('click', function () {
        let val = parseInt(input.value) || 1;
        if (val > 1) {
          input.value = val - 1;
          input.dispatchEvent(new Event('change'));
        }
      });
    }

    if (btnPlus) {
      btnPlus.addEventListener('click', function () {
        let val = parseInt(input.value) || 1;
        if (val < maxStock) {
          input.value = val + 1;
          input.dispatchEvent(new Event('change'));
        }
      });
    }
  });

  // 3. Image Upload Preview
  const imageInputs = document.querySelectorAll('.image-upload-input');
  imageInputs.forEach(function (input) {
    input.addEventListener('change', function () {
      const targetPreviewId = input.getAttribute('data-preview-target');
      if (!targetPreviewId) return;

      const previewElement = document.getElementById(targetPreviewId);
      if (!previewElement) return;

      const file = input.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
          previewElement.src = e.target.result;
          previewElement.classList.remove('d-none');
        };
        reader.readAsDataURL(file);
      }
    });
  });

  // 4. Simulated Checkout Payment Selector Tabs
  const paymentRadios = document.querySelectorAll('input[name="payment_method"]');
  const cardSection = document.getElementById('card-payment-details');
  const upiSection = document.getElementById('upi-payment-details');
  const codSection = document.getElementById('cod-payment-details');

  function updatePaymentVisibility() {
    const selected = document.querySelector('input[name="payment_method"]:checked');
    if (!selected) return;

    const val = selected.value;
    if (cardSection) cardSection.classList.toggle('d-none', val !== 'Credit/Debit Card');
    if (upiSection) upiSection.classList.toggle('d-none', val !== 'UPI / QR');
    if (codSection) codSection.classList.toggle('d-none', val !== 'Cash on Delivery');
  }

  paymentRadios.forEach(function (radio) {
    radio.addEventListener('change', updatePaymentVisibility);
  });
  updatePaymentVisibility();

  // 5. Card Number Auto-formatting (4-4-4-4)
  const cardInput = document.getElementById('card_number');
  if (cardInput) {
    cardInput.addEventListener('input', function (e) {
      let value = e.target.value.replace(/\D/g, '');
      let formatted = value.match(/.{1,4}/g)?.join(' ') || '';
      e.target.value = formatted.substring(0, 19);
    });
  }

  // 6. Card Expiry Auto-formatting (MM/YY)
  const expInput = document.getElementById('card_expiry');
  if (expInput) {
    expInput.addEventListener('input', function (e) {
      let value = e.target.value.replace(/\D/g, '');
      if (value.length >= 2) {
        e.target.value = value.substring(0, 2) + '/' + value.substring(2, 4);
      } else {
        e.target.value = value;
      }
    });
  }

  // 7. Scroll-Triggered Reveal Animations (IntersectionObserver)
  const revealElements = document.querySelectorAll('.reveal-on-scroll');
  if ('IntersectionObserver' in window && revealElements.length > 0) {
    const revealObserver = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      threshold: 0.12,
      rootMargin: '0px 0px -40px 0px'
    });

    revealElements.forEach(function (el) {
      revealObserver.observe(el);
    });
  } else {
    // Fallback for browsers without IntersectionObserver
    revealElements.forEach(function (el) {
      el.classList.add('is-visible');
    });
  }

  // 8. Animated Stats Counter
  const statNumbers = document.querySelectorAll('.stat-number');
  if ('IntersectionObserver' in window && statNumbers.length > 0) {
    const countObserver = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const el = entry.target;
          const rawText = el.textContent.trim();
          const targetNum = parseInt(rawText.replace(/\D/g, ''), 10);
          const hasPlus = rawText.includes('+');

          if (!isNaN(targetNum) && targetNum > 0) {
            let current = 0;
            const duration = 1600;
            const stepTime = Math.max(Math.floor(duration / targetNum), 20);
            const increment = Math.ceil(targetNum / (duration / stepTime));

            const timer = setInterval(function () {
              current += increment;
              if (current >= targetNum) {
                current = targetNum;
                clearInterval(timer);
              }
              el.textContent = current + (hasPlus ? '+' : '');
            }, stepTime);
          }

          observer.unobserve(el);
        }
      });
    }, { threshold: 0.3 });

    statNumbers.forEach(function (stat) {
      countObserver.observe(stat);
    });
  }

  // 9. Hero Video Autoplay Guardian
  const heroVideo = document.querySelector('.hero-video');
  if (heroVideo) {
    heroVideo.muted = true;
    const playPromise = heroVideo.play();
    if (playPromise !== undefined) {
      playPromise.catch(function () {
        // Autoplay prevented by browser power settings or policy; keep poster image visible
      });
    }
  }
});
