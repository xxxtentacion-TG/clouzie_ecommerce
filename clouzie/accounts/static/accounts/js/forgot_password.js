
document.getElementById("sendOtpBtn").addEventListener("click", function(e) {
    e.preventDefault();

    const email = document.getElementById("email").value;

    fetch("", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": "{{ csrf_token }}"
        },
        body: new URLSearchParams({
            email: email
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // redirect after OTP sent
            window.location.href = "{% url 'verify_otp' %}";
        }
    })
    .catch(error => console.log(error));
});