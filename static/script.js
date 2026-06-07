document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('form');
    const loader = document.getElementById('loader');
    const predictBtn = document.getElementById('predictBtn');

    if (form) {
        form.addEventListener('submit', () => {
            if (loader) loader.style.display = 'block';
            if (predictBtn) {
                predictBtn.disabled = true;
                predictBtn.innerText = 'Processing...';
            }
        });
    }

    // Dynamic color for probability if element exists
    const probElement = document.getElementById('probabilityScale');
    if (probElement) {
        const val = parseFloat(probElement.innerText);
        if (val > 50) {
            probElement.style.color = '#e74c3c';
        } else {
            probElement.style.color = '#27ae60';
        }
    }
});
