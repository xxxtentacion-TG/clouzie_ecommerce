tailwind.config = {
    theme: {
    extend: {
        fontFamily: {
        serif: ['"Playfair Display"', 'serif'],
        sans: ['Inter', 'sans-serif'],
        },
    }
    }
}

// Toggle password visibility

function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);

    if (input.type === "password") {
        input.type = "text";
        btn.innerHTML = "🙈"; // change icon
    } else {
        input.type = "password";
        btn.innerHTML = "👁"; // change back
    }
}