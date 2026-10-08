(function () {
	function is_login_page() {
		return document.body && document.body.getAttribute("data-path") === "login";
	}

	function render_visual_panel() {
		var visual = document.createElement("aside");
		visual.className = "tms-login-visual";
		visual.setAttribute("aria-label", "AL RANA transport image");
		return visual;
	}

	function update_login_text() {
		var buttons = document.querySelectorAll(".btn-login");
		Array.prototype.forEach.call(buttons, function (button) {
			if (button.textContent.trim() === "Continue") {
				button.textContent = "Sign In";
			}
		});
	}

	function bind_loading_state() {
		var forms = document.querySelectorAll(".form-login");
		Array.prototype.forEach.call(forms, function (form) {
			if (form.getAttribute("data-tms-loading-bound")) {
				return;
			}
			form.setAttribute("data-tms-loading-bound", "1");
			form.addEventListener("submit", function () {
				var button = form.querySelector(".btn-login");
				if (button) {
					button.classList.add("tms-loading");
				}
			});
		});

		if (!window.MutationObserver) {
			return;
		}

		var observer = new MutationObserver(function () {
			var banners = document.querySelectorAll(".login-error-banner");
			Array.prototype.forEach.call(banners, function (banner) {
				if (banner.offsetParent !== null && banner.textContent.trim()) {
					var loading_buttons = document.querySelectorAll(".btn-login.tms-loading");
					Array.prototype.forEach.call(loading_buttons, function (button) {
						button.classList.remove("tms-loading");
					});
				}
			});
		});

		var banners = document.querySelectorAll(".login-error-banner");
		Array.prototype.forEach.call(banners, function (banner) {
			observer.observe(banner, { attributes: true, childList: true, subtree: true });
		});
	}

	function enhance_login() {
		if (!is_login_page() || document.querySelector(".tms-login-shell")) {
			return;
		}

		var page_content = document.querySelector("main .page_content");
		if (!page_content) {
			return;
		}

		document.documentElement.classList.add("tms-login-html");
		document.body.classList.add("tms-login-page");
		update_login_text();

		var shell = document.createElement("div");
		shell.className = "tms-login-shell";

		var form_panel = document.createElement("div");
		form_panel.className = "tms-login-form-panel";

		var form_inner = document.createElement("div");
		form_inner.className = "tms-login-form-inner";

		while (page_content.firstChild) {
			form_inner.appendChild(page_content.firstChild);
		}

		form_panel.appendChild(form_inner);
		shell.appendChild(render_visual_panel());
		shell.appendChild(form_panel);
		page_content.appendChild(shell);
		bind_loading_state();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", enhance_login);
	} else {
		enhance_login();
	}

	if (window.frappe && frappe.ready) {
		frappe.ready(enhance_login);
	}
})();
