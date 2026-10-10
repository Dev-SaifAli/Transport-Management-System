/* ==========================================================================
   AL RANA Transport Management - login page UI polish
   --------------------------------------------------------------------------
   Tiny, dependency-free helper for transport_management/www/login.html.

   It only adds UI niceties on top of Frappe's own `templates/includes/login/
   login.js`, which is included verbatim by the template and keeps submitting,
   validating, OTP/2FA, the password toggle and redirects working.

   None of this file talks to a server and none of it references new
   endpoints: "Login with Email Link" still goes through the existing
   frappe.www.login.send_login_link hook wired up by login.js.
   ========================================================================== */
(function () {
	"use strict";

	var SUBMITTING_CLASS = "al-is-submitting";
	var ROUTE_ATTR = "data-al-route";

	/** Run `fn` as soon as the markup is available. */
	function whenReady(fn) {
		// The script tag sits at the end of <body>, so the markup is already
		// parsed. Fall back to DOMContentLoaded only if that ever changes.
		if (document.querySelector(".al-login")) {
			fn();
		} else {
			document.addEventListener("DOMContentLoaded", fn, { once: true });
		}
	}

	/** The re-skinned template always renders this wrapper. */
	function getLoginRoot() {
		return document.querySelector(".al-login");
	}

	function getFormWrap() {
		return document.querySelector(".al-form-wrap");
	}

	/**
	 * Remember which login view is active so the stylesheet can pick between
	 * the re-skin header ("Welcome back") and the stock section title.
	 */
	function syncRouteClass() {
		var wrap = getFormWrap();
		if (!wrap) return;
		var route = (window.location.hash || "#login").slice(1) || "login";
		wrap.setAttribute(ROUTE_ATTR, route.replace(/-/g, "_"));
	}

	/** Show a "Caps Lock is on" hint on the password field. */
	function initCapsLockHint() {
		var input = document.getElementById("login_password");
		var hint = document.getElementById("al_caps_hint");
		if (!input || !hint) return;

		var text = hint.getAttribute("data-caps-text") || "Caps Lock is on";

		var update = function (event) {
			var caps = false;
			if (event && typeof event.getModifierState === "function") {
				caps = event.getModifierState("CapsLock");
			}
			hint.classList.toggle("al-is-visible", !!caps);
			hint.textContent = caps ? text : "";
		};

		input.addEventListener("keydown", update);
		input.addEventListener("keyup", update);
		input.addEventListener("blur", function () {
			hint.classList.remove("al-is-visible");
			hint.textContent = "";
		});
	}

	/**
	 * Keep the password visibility toggle accessible: login.js already toggles
	 * the input type and swaps the icon, this only mirrors it in ARIA state and
	 * adds keyboard activation. The state is tracked locally because login.js
	 * binds its own handler depending on script order, so the current DOM value
	 * of the input cannot be relied upon at click time.
	 */
	function initPasswordToggle() {
		var toggles = document.querySelectorAll(".toggle-password");
		Array.prototype.forEach.call(toggles, function (toggle) {
			var selector = toggle.getAttribute("toggle");
			if (!selector) return;

			var showLabel = toggle.getAttribute("data-label-show") || "Show password";
			var hideLabel = toggle.getAttribute("data-label-hide") || "Hide password";

			var input = document.querySelector(selector);
			var visible = !!(input && input.getAttribute("type") !== "password");

			var apply = function () {
				toggle.setAttribute("aria-pressed", visible ? "true" : "false");
				toggle.setAttribute("aria-label", visible ? hideLabel : showLabel);
				toggle.setAttribute("role", "button");
			};

			toggle.addEventListener("click", function () {
				visible = !visible;
				apply();
			});
			toggle.addEventListener("keydown", function (event) {
				if (event.key === "Enter" || event.key === " " || event.key === "Spacebar") {
					event.preventDefault();
					toggle.click();
				}
			});
			apply();
		});
	}

	/**
	 * Loading state for the submit buttons: disable the fields and show a
	 * spinner while the request is in flight. It is skipped when login.js only
	 * reported a validation error, and it is dropped as soon as Frappe's own
	 * request finishes (the `#freeze` overlay it shows for `freeze: true` is
	 * removed), so the UI can never get stuck.
	 */
	function initLoadingState() {
		var forms = document.querySelectorAll(".al-form-wrap form.form-signin");
		if (!forms.length || !document.body) return;

		var setDisabled = function (form, disabled) {
			var fields = form.querySelectorAll("input, button[type='submit']");
			Array.prototype.forEach.call(fields, function (field) {
				field.disabled = disabled;
			});
		};

		var stop = function () {
			var active = document.querySelectorAll("." + SUBMITTING_CLASS);
			Array.prototype.forEach.call(active, function (form) {
				form.classList.remove(SUBMITTING_CLASS);
				setDisabled(form, false);
			});
		};

		// Frappe shows the error / success banner by giving it an inline
		// `display: flex`, so watching that attribute also tells us the
		// request is over.
		var watchBanners = function () {
			var banners = document.querySelectorAll(
				".al-form-wrap .login-error-banner, .al-form-wrap .login-success-banner"
			);
			Array.prototype.forEach.call(banners, function (banner) {
				if (banner.getAttribute("data-al-watched")) return;
				banner.setAttribute("data-al-watched", "1");
				var observer = new MutationObserver(function () {
					if (banner.style.display && banner.style.display.indexOf("flex") > -1) {
						stop();
					}
				});
				observer.observe(banner, { attributes: true, childList: true, subtree: true });
			});
		};

		// login.js calls frappe.call with `freeze: true`, which renders the
		// `#freeze` overlay and removes it again when the response is back.
		var wasFrozen = false;
		var onBodyChange = function () {
			var frozen = !!document.getElementById("freeze");
			if (wasFrozen && !frozen) stop();
			wasFrozen = frozen;
		};
		new MutationObserver(onBodyChange).observe(document.body, {
			childList: true,
			subtree: true,
		});

		// Delegated so the OTP / 2FA form that login.js injects at runtime is
		// covered too.
		document.addEventListener("submit", function (event) {
			var form = event.target;
			if (!form || !form.classList) return;
			if (!form.classList.contains("form-signin") && !form.classList.contains("form-verify")) {
				return;
			}
			// Defer one tick so login.js can run its own synchronous
			// validation and mark the failing fields first.
			window.setTimeout(function () {
				var invalid = form.querySelectorAll(".form-group.invalid").length;
				if (invalid) return;
				stop();
				form.classList.add(SUBMITTING_CLASS);
				setDisabled(form, true);
				// Safety net in case no banner and no overlay ever appear.
				window.setTimeout(stop, 30000);
			}, 0);
		});

		watchBanners();
	}

	whenReady(function () {
		if (!getLoginRoot()) return;
		syncRouteClass();
		initCapsLockHint();
		initPasswordToggle();
		initLoadingState();
		window.addEventListener("hashchange", syncRouteClass);
	});

	if (window.frappe && typeof window.frappe.ready === "function") {
		window.frappe.ready(function () {
			if (getLoginRoot()) syncRouteClass();
		});
	}
})();
