// =========================
// OTP INPUT HANDLING
// =========================
const inputs = document.querySelectorAll('.otp-input');

// Auto move + backspace
inputs.forEach((input, index) => {

  input.addEventListener('input', (e) => {
    const value = e.target.value;

    // Only allow numbers
    e.target.value = value.replace(/[^0-9]/g, '');

    if (value.length === 1 && index < inputs.length - 1) {
      inputs[index + 1].focus();
    }
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' && !e.target.value && index > 0) {
      inputs[index - 1].focus();
    }
  });

});


// =========================
// 📋 PASTE FULL OTP
// =========================
inputs[0].addEventListener('paste', (e) => {
  const pasteData = e.clipboardData.getData('text').trim();

  if (/^\d{6}$/.test(pasteData)) {
    inputs.forEach((input, i) => {
      input.value = pasteData[i];
    });
  }
});


// =========================
// ⏱ OTP TIMER (5 MIN)
// =========================
let otpTime = 300;
const timerEl = document.getElementById('timer');
const verifyBtn = document.querySelector('button[type="submit"]');

const otpCountdown = setInterval(() => {

  let minutes = Math.floor(otpTime / 60);
  let seconds = otpTime % 60;

  seconds = seconds < 10 ? '0' + seconds : seconds;
  timerEl.innerText = `${minutes}:${seconds}`;

  otpTime--;

  if (otpTime < 0) {
    clearInterval(otpCountdown);

    timerEl.innerText = "Expired";

    verifyBtn.disabled = true;
    verifyBtn.classList.add("opacity-40", "cursor-not-allowed");

    inputs.forEach(input => input.value = '');
  }

}, 1000);


// =========================
// 🔁 RESEND TIMER (1 MIN)
// =========================
let resendTime = 60;
const resendBtn = document.getElementById("resendBtn");

function startResendTimer() {
  resendBtn.disabled = true;
  resendBtn.classList.remove("resend-active");
  resendBtn.classList.add("resend-disabled");

  const timer = setInterval(() => {

    resendTime--;
    resendBtn.innerText = `Resend Code (${resendTime}s)`;

    if (resendTime <= 0) {
      clearInterval(timer);

      resendBtn.disabled = false;
      resendBtn.innerText = "Resend Code";

      resendBtn.classList.remove("resend-disabled");
      resendBtn.classList.add("resend-active");
    }

  }, 1000);
}

startResendTimer();


// =========================
// 🔁 RESEND CLICK
// =========================
resendBtn.addEventListener("click", () => {

  resendBtn.innerText = "Sending...";

  fetch("/forgot-resend-otp/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    }
  })
  .then(res => res.json())
  .then(data => {

    if (data.success) {

      resendTime = 60;
      startResendTimer();

      otpTime = 300;

      verifyBtn.disabled = false;
      verifyBtn.classList.remove("opacity-40");

      inputs.forEach(input => input.value = '');
      inputs[0].focus();

    } else {
      alert("Error resending OTP");
    }

  });

});

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}