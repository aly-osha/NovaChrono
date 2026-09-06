/**
 * NovaChrono Main Interactive JavaScript
 * "Collect. Discover. Trade."
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Sticky Nav state
  const nav = document.querySelector('.chrono-nav');
  if (nav) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 30) {
        nav.classList.add('scrolled');
      } else {
        nav.classList.remove('scrolled');
      }
    });
  }

  // 2. User Menu Dropdown Toggle
  const userPill = document.getElementById('userPillBtn');
  const userDropdown = document.getElementById('userDropdownMenu');
  if (userPill && userDropdown) {
    userPill.addEventListener('click', (e) => {
      e.stopPropagation();
      userDropdown.classList.toggle('show');
    });
    document.addEventListener('click', () => {
      userDropdown.classList.remove('show');
    });
  }

  // 3. Search Autocomplete Modal
  const searchTrigger = document.getElementById('navSearchBtn');
  const searchBackdrop = document.getElementById('searchModalBackdrop');
  const searchClose = document.getElementById('searchModalClose');
  const searchInput = document.getElementById('searchLiveInput');
  const searchResults = document.getElementById('searchSuggestionsContainer');

  if (searchTrigger && searchBackdrop) {
    searchTrigger.addEventListener('click', () => {
      searchBackdrop.classList.add('show');
      if (searchInput) searchInput.focus();
    });

    if (searchClose) {
      searchClose.addEventListener('click', () => {
        searchBackdrop.classList.remove('show');
      });
    }

    searchBackdrop.addEventListener('click', (e) => {
      if (e.target === searchBackdrop) {
        searchBackdrop.classList.remove('show');
      }
    });

    // Debounced Live Search
    let searchTimer = null;
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        const query = e.target.value.trim();
        if (query.length < 2) {
          if (searchResults) searchResults.innerHTML = '<p style="color:var(--text-muted); padding:12px;">Type at least 2 characters to search...</p>';
          return;
        }

        searchTimer = setTimeout(() => {
          fetch(`/api/search-suggest/?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
              if (!searchResults) return;
              if (data.results.length === 0) {
                searchResults.innerHTML = '<p style="color:var(--text-muted); padding:12px;">No cards or products found matching your search.</p>';
                return;
              }
              searchResults.innerHTML = data.results.map(item => `
                <a href="${item.url}" class="search-suggestion-item">
                  <img src="${item.image}" alt="${item.name}" style="width:48px; height:48px; object-fit:contain; border-radius:8px; background:#F3EFE6; padding:4px;">
                  <div style="flex:1;">
                    <div style="font-weight:600; font-size:0.95rem; color:var(--text-primary);">${item.name}</div>
                    <div style="font-size:0.8rem; color:var(--text-muted);">${item.tcg} · ${item.category}</div>
                  </div>
                  <div style="font-weight:700; font-family:var(--font-heading); color:var(--accent-cosmic);">${item.price}</div>
                </a>
              `).join('');
            })
            .catch(err => console.error(err));
        }, 250);
      });
    }
  }

  // 4. Quick View Modal
  const quickViewBackdrop = document.getElementById('quickViewBackdrop');
  const quickViewClose = document.getElementById('quickViewClose');
  const quickViewContent = document.getElementById('quickViewBody');

  document.querySelectorAll('.btn-quick-view').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const prodId = btn.getAttribute('data-product-id');
      if (!prodId || !quickViewBackdrop) return;

      quickViewBackdrop.classList.add('show');
      if (quickViewContent) {
        quickViewContent.innerHTML = `
          <div style="text-align:center; padding:40px;">
            <div style="display:inline-block; width:36px; height:36px; border:3px solid var(--accent-cosmic); border-top-color:transparent; border-radius:50%; animation:spin 0.8s linear infinite;"></div>
            <p style="margin-top:12px; color:var(--text-muted);">Summoning card data...</p>
          </div>
        `;
      }

      fetch(`/api/quick-view/${prodId}/`)
        .then(res => res.json())
        .then(prod => {
          if (!quickViewContent) return;
          quickViewContent.innerHTML = `
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:32px; align-items:center;">
              <div style="background:#F3EFE6; border-radius:var(--radius-lg); padding:20px; text-align:center;">
                <img src="${prod.primary_image}" alt="${prod.name}" style="max-height:300px; max-width:100%; margin:0 auto; object-fit:contain;">
              </div>
              <div>
                <span class="badge-tag badge-tcg" style="margin-bottom:8px;">${prod.tcg}</span>
                <h3 style="font-size:1.35rem; margin-bottom:8px;">${prod.name}</h3>
                <div style="display:flex; align-items:baseline; gap:8px; margin-bottom:12px;">
                  <span style="font-family:var(--font-heading); font-size:1.4rem; font-weight:700; color:var(--text-primary);">$${prod.price}</span>
                  ${prod.compare_at_price ? `<span style="text-decoration:line-through; color:var(--text-muted);">$${prod.compare_at_price}</span>` : ''}
                </div>
                <p style="font-size:0.88rem; color:var(--text-secondary); margin-bottom:16px;">${prod.short_description}</p>
                <div style="font-size:0.82rem; margin-bottom:18px; color:var(--text-muted); display:flex; flex-direction:column; gap:4px;">
                  <div><b>Condition:</b> ${prod.condition}</div>
                  <div><b>Edition:</b> ${prod.edition}</div>
                  <div><b>Status:</b> <span style="color:${prod.is_in_stock ? 'var(--accent-mint)' : '#E53935'}; font-weight:600;">${prod.stock_status}</span></div>
                </div>
                <div style="display:flex; gap:10px;">
                  <form action="/cart/add/${prod.id}/" method="POST" class="ajax-cart-form" style="flex:1;">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
                    <input type="hidden" name="quantity" value="1">
                    <button type="submit" class="btn-chrono btn-chrono-cosmic" style="width:100%;">
                      Add to Vault Cart
                    </button>
                  </form>
                  <a href="${prod.detail_url}" class="btn-chrono btn-chrono-outline">View Details</a>
                </div>
              </div>
            </div>
          `;
          bindAjaxCartForms();
        })
        .catch(err => console.error(err));
    });
  });

  if (quickViewClose && quickViewBackdrop) {
    quickViewClose.addEventListener('click', () => {
      quickViewBackdrop.classList.remove('show');
    });
    quickViewBackdrop.addEventListener('click', (e) => {
      if (e.target === quickViewBackdrop) quickViewBackdrop.classList.remove('show');
    });
  }

  // 5. AJAX Add to Cart
  function bindAjaxCartForms() {
    document.querySelectorAll('.ajax-cart-form').forEach(form => {
      if (form.getAttribute('data-bound')) return;
      form.setAttribute('data-bound', 'true');

      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');
        const origText = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) submitBtn.innerHTML = 'Adding...';

        const formData = new FormData(form);
        fetch(form.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
          }
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            if (submitBtn) {
              submitBtn.innerHTML = '✓ Added to Cart';
              submitBtn.classList.add('added');
              setTimeout(() => {
                submitBtn.innerHTML = origText;
                submitBtn.classList.remove('added');
              }, 2000);
            }
            // Update nav cart badge
            const cartBadges = document.querySelectorAll('.nav-cart-badge');
            cartBadges.forEach(b => {
              b.textContent = data.cart_count;
              b.style.display = data.cart_count > 0 ? 'flex' : 'none';
            });
            showToast(data.message || 'Item added to cart!');
          } else {
            showToast(data.message || 'Unable to add item', 'error');
            if (submitBtn) submitBtn.innerHTML = origText;
          }
        })
        .catch(err => {
          console.error(err);
          if (submitBtn) submitBtn.innerHTML = origText;
        });
      });
    });
  }
  bindAjaxCartForms();

  // 6. AJAX Wishlist Toggle
  document.querySelectorAll('.btn-wishlist-toggle').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const prodId = btn.getAttribute('data-product-id');
      if (!prodId) return;

      fetch(`/wishlist/toggle/${prodId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCSRFToken(),
        }
      })
      .then(res => res.json())
      .then(data => {
        if (data.login_required) {
          showToast(data.message, 'info');
          setTimeout(() => {
            window.location.href = data.login_url;
          }, 1000);
          return;
        }

        if (data.success) {
          if (data.is_in_wishlist) {
            btn.classList.add('active');
            btn.innerHTML = '♥';
          } else {
            btn.classList.remove('active');
            btn.innerHTML = '♡';
          }

          const wishBadges = document.querySelectorAll('.nav-wishlist-badge');
          wishBadges.forEach(b => {
            b.textContent = data.wishlist_count;
            b.style.display = data.wishlist_count > 0 ? 'flex' : 'none';
          });
          showToast(data.message);
        }
      })
      .catch(err => console.error(err));
    });
  });

  // 7. Dynamic Cart Quantity Controls
  document.querySelectorAll('.btn-cart-qty').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const itemId = btn.getAttribute('data-item-id');
      const action = btn.getAttribute('data-action');
      if (!itemId || !action) return;

      const formData = new FormData();
      formData.append('action', action);

      fetch(`/cart/update/${itemId}/`, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCSRFToken(),
        }
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          if (data.item_removed) {
            const row = document.getElementById(`cartRow-${itemId}`);
            if (row) row.remove();
          } else {
            const qtyElem = document.getElementById(`qtyVal-${itemId}`);
            if (qtyElem) qtyElem.textContent = data.item_quantity;
            const lineTotalElem = document.getElementById(`lineTotal-${itemId}`);
            if (lineTotalElem) lineTotalElem.textContent = data.line_total;
          }

          // Summary fields
          const subtotalElem = document.getElementById('cartSummarySubtotal');
          if (subtotalElem) subtotalElem.textContent = data.subtotal;
          const taxElem = document.getElementById('cartSummaryTax');
          if (taxElem) taxElem.textContent = data.tax;
          const shippingElem = document.getElementById('cartSummaryShipping');
          if (shippingElem) shippingElem.textContent = data.shipping;
          const totalElem = document.getElementById('cartSummaryTotal');
          if (totalElem) totalElem.textContent = data.total;

          // Update nav cart badge
          const cartBadges = document.querySelectorAll('.nav-cart-badge');
          cartBadges.forEach(b => {
            b.textContent = data.cart_count;
            b.style.display = data.cart_count > 0 ? 'flex' : 'none';
          });

          if (data.cart_count === 0) {
            window.location.reload();
          }
        }
      })
      .catch(err => console.error(err));
    });
  });

  // Helper: CSRF token retrieval
  function getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }

  // Helper: Toast Notifications
  function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'chrono-toast';
    const icon = type === 'error' ? '✕' : (type === 'info' ? 'ℹ' : '✓');
    toast.innerHTML = `<span style="font-size:1.1rem; color:${type === 'error' ? '#FF5A5A' : 'var(--accent-gold)'}">${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 400);
    }, 3200);
  }
});
