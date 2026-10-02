(function () {
	function is_login_page() {
		return document.body && document.body.getAttribute("data-path") === "login";
	}

	function render_brand_header() {
		return [
			'<div class="tms-login-brand" aria-label="AL RANA TRANSPORT LLC">',
			'<div class="tms-login-logo-row">',
			'<div class="tms-login-logo" aria-hidden="true">AR</div>',
			'<div class="tms-login-company-name">AL RANA TRANSPORT LLC</div>',
			"</div>",
			"<h1>Welcome Back</h1>",
			"<p>Sign in to your TMS account</p>",
			"</div>",
		].join("");
	}

	function render_visual_panel() {
		var visual = document.createElement("aside");
		visual.className = "tms-login-visual";
		visual.setAttribute("aria-label", "Transport Management System");
		visual.innerHTML = [
			'<div class="tms-login-visual-content">',
			'<div class="tms-login-kicker">AL RANA TRANSPORT LLC</div>',
			"<h2>Transport Management System</h2>",
			"<p>Moving Business Forward</p>",
			"</div>",
		].join("");
		return visual;
	}

	function update_login_text() {
		var labels = document.querySelectorAll('label[for="login_email"]');
		Array.prototype.forEach.call(labels, function (label) {
			label.textContent = "Email or Username";
		});

		var headings = document.querySelectorAll(".for-login .page-card-head h4, .for-email-login .page-card-head h4");
		Array.prototype.forEach.call(headings, function (heading) {
			heading.textContent = "Welcome Back";
		});

		var subtitles = document.querySelectorAll(".for-login .page-card-subtitle, .for-email-login .page-card-subtitle");
		Array.prototype.forEach.call(subtitles, function (subtitle) {
			subtitle.textContent = "Sign in to your TMS account";
		});

		var buttons = document.querySelectorAll(".btn-login");
		Array.prototype.forEach.call(buttons, function (button) {
			if (button.textContent.trim() === "Continue") {
				button.textContent = "Sign In";
			}
		});
	}

	function add_footer(form_inner) {
		if (form_inner.querySelector(".tms-login-footer")) {
			return;
		}
		var footer = document.createElement("div");
		footer.className = "tms-login-footer";
		footer.innerHTML = '© AL RANA TRANSPORT LLC <span aria-hidden="true">|</span> <a href="mailto:support@example.com">Support</a>';
		form_inner.appendChild(footer);
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
		form_inner.innerHTML = render_brand_header();

		while (page_content.firstChild) {
			form_inner.appendChild(page_content.firstChild);
		}

		add_footer(form_inner);
		form_panel.appendChild(form_inner);
		shell.appendChild(form_panel);
		shell.appendChild(render_visual_panel());
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
