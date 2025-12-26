document.addEventListener('DOMContentLoaded', function () {
    const forms = document.getElementsByTagName('form');

    forms.forEach(form => {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid && typeof firstInvalid.focus === 'function') {
                    firstInvalid.focus();
                }
            }

            form.classList.add('was-validated');
        },false); 
    });
});