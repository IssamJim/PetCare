(() => {
  "use strict";

  const notifyErrors = (errors, focusTarget) => {
    const text = errors.join("\n");
    if (window.Swal) {
      window.Swal.fire({
        icon: "error",
        title: "No se pudo completar el registro",
        text,
        confirmButtonText: "Corregir datos",
        confirmButtonColor: "#007bff",
      }).then(() => focusTarget?.focus());
    } else {
      window.alert(`No se pudo completar el registro.\n${text}`);
      focusTarget?.focus();
    }
  };

  const success = document.getElementById("registration-success");
  if (success && window.Swal) {
    window.Swal.fire({
      icon: "success",
      title: "¡Registro exitoso!",
      text: "Tu cuenta ha sido creada correctamente.",
      confirmButtonText: "Iniciar sesión",
      confirmButtonColor: "#007bff",
      allowOutsideClick: false,
      allowEscapeKey: false,
    }).then((result) => {
      if (result.isConfirmed) window.location.assign(success.dataset.loginUrl);
    });
  }

  const form = document.getElementById("registration-form");
  if (!form) return;
  // Native constraints still work without JS. With JS, show one Spanish popup.
  form.noValidate = true;
  const inputs = Array.from(form.querySelectorAll("input:not([type=hidden])"));
  const button = document.getElementById("registration-submit");
  const status = document.getElementById("registration-status");
  let submitting = false;

  const labelFor = (input) => input.labels[0].textContent.replace("*", "").trim();
  const validate = (input, trim = false) => {
    if (trim && input.type !== "password") input.value = input.value.trim();
    let error = "";
    if (input.validity.valueMissing || (input.type !== "password" && !input.value.trim())) {
      error = `Completa el campo ${labelFor(input).toLocaleLowerCase("es")}.`;
    } else if (input.type === "email" && input.validity.typeMismatch) {
      error = "Por favor, introduce un correo electrónico válido.";
    } else if (input.validity.tooLong) {
      error = `Usa como máximo ${input.maxLength} caracteres.`;
    } else if (input.name === "password2" && input.value !== form.elements.password1.value) {
      error = "Las contraseñas no coinciden.";
    }
    const errorBox = document.getElementById(`${input.id}_errors`);
    errorBox.textContent = error;
    input.classList.toggle("is-invalid", Boolean(error));
    if (error) input.setAttribute("aria-invalid", "true");
    else input.removeAttribute("aria-invalid");
    return error;
  };

  inputs.forEach((input) => {
    input.addEventListener("blur", () => {
      input.dataset.touched = "true";
      validate(input, true);
    });
    input.addEventListener("input", () => {
      if (input.dataset.touched || input.hasAttribute("aria-invalid")) validate(input);
      if (input.name === "password1" && form.elements.password2.dataset.touched) {
        validate(form.elements.password2);
      }
    });
  });

  form.addEventListener("submit", (event) => {
    if (submitting) {
      event.preventDefault();
      return;
    }
    const errors = inputs.map((input) => {
      input.dataset.touched = "true";
      const error = validate(input, true);
      return error ? `${labelFor(input)}: ${error}` : "";
    }).filter(Boolean);
    if (errors.length) {
      event.preventDefault();
      notifyErrors(errors, form.querySelector('[aria-invalid="true"]'));
      return;
    }
    submitting = true;
    button.disabled = true;
    button.textContent = "Creando cuenta…";
    status.textContent = "Estamos procesando tu registro. Espera un momento.";
    form.setAttribute("aria-busy", "true");
  });

  window.addEventListener("pageshow", () => {
    submitting = false;
    button.disabled = false;
    button.textContent = "Registrarse";
    status.textContent = "";
    form.removeAttribute("aria-busy");
  });

  const serverErrors = JSON.parse(document.getElementById("registration-errors").textContent);
  if (serverErrors.length) notifyErrors(serverErrors, form.querySelector('[aria-invalid="true"]'));
})();
