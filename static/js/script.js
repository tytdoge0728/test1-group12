// static/js/script.js
document.addEventListener("DOMContentLoaded", () => {
    const tokenInput = document.getElementById("github_token");
    // 範例：當輸入值不滿 40 字元，則在輸入框下方顯示警告
    tokenInput.addEventListener("input", () => {
      if (tokenInput.value.length < 40) {
        tokenInput.classList.add("is-invalid");
      } else {
        tokenInput.classList.remove("is-invalid");
      }
    });
  });
  