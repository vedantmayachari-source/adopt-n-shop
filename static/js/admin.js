// Adopt n Shop - Admin Dashboard Charts & Interactions

document.addEventListener('DOMContentLoaded', function () {
  // 1. Mobile Sidebar Toggle
  const sidebarToggle = document.getElementById('sidebarToggle');
  const adminSidebar = document.querySelector('.admin-sidebar');
  if (sidebarToggle && adminSidebar) {
    sidebarToggle.addEventListener('click', function () {
      adminSidebar.classList.toggle('show');
    });
  }

  // 2. Load Analytics Charts if Chart.js is loaded and canvas exists
  const speciesCanvas = document.getElementById('speciesChart');
  const categoryCanvas = document.getElementById('categoryChart');
  const orderCanvas = document.getElementById('orderStatusChart');

  if (typeof Chart !== 'undefined' && (speciesCanvas || categoryCanvas || orderCanvas)) {
    fetch('/admin/api/analytics')
      .then(response => response.json())
      .then(data => {
        // Chart 1: Pets by Species (Doughnut)
        if (speciesCanvas && data.species) {
          new Chart(speciesCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
              labels: data.species.labels,
              datasets: [{
                data: data.species.counts,
                backgroundColor: [
                  '#183D32', // Forest Green
                  '#F28C45', // Sunset Orange
                  '#A8B9A0', // Sage Green
                  '#252D27', // Charcoal
                  '#EBDDC7', // Warm Cream Accent
                  '#819578'  // Dark Sage
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { position: 'bottom' }
              },
              cutout: '65%'
            }
          });
        }

        // Chart 2: Products by Category (Bar)
        if (categoryCanvas && data.categories) {
          new Chart(categoryCanvas.getContext('2d'), {
            type: 'bar',
            data: {
              labels: data.categories.labels,
              datasets: [{
                label: 'Products',
                data: data.categories.counts,
                backgroundColor: '#183D32',
                borderRadius: 8,
                maxBarThickness: 45
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  ticks: { precision: 0 }
                },
                x: {
                  grid: { display: false }
                }
              }
            }
          });
        }

        // Chart 3: Order Status Breakdown (Polar/Pie)
        if (orderCanvas && data.order_statuses) {
          new Chart(orderCanvas.getContext('2d'), {
            type: 'pie',
            data: {
              labels: data.order_statuses.labels,
              datasets: [{
                data: data.order_statuses.counts,
                backgroundColor: [
                  '#f59e0b', // Pending (amber)
                  '#F28C45', // Processing (Sunset Orange)
                  '#A8B9A0', // Shipped (Sage Green)
                  '#183D32', // Delivered (Forest Green)
                  '#ef4444'  // Cancelled (red)
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { position: 'bottom' }
              }
            }
          });
        }
      })
      .catch(err => console.error('Failed to load chart analytics data:', err));
  }
});
