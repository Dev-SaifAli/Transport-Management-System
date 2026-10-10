// Shared helpers for the AL RANA Dispatch console views.
// Loaded through the `page_js` hook before the section views.

frappe.provide("dispatch_portal");

dispatch_portal.utils = {
	escape(value) {
		if (value === null || value === undefined) {
			return "";
		}
		return String(value)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#39;");
	},

	text(value, fallback) {
		if (value === null || value === undefined || value === "") {
			return `<span class="al-dispatch-muted">${this.escape(fallback || "-")}</span>`;
		}
		return this.escape(value);
	},

	format_number(value, precision) {
		const number = Number(value || 0);
		return number.toLocaleString(undefined, {
			maximumFractionDigits: precision === undefined ? 2 : precision,
		});
	},

	format_datetime(value) {
		if (!value) {
			return "<span class=\"al-dispatch-muted\">-</span>";
		}
		const date = new Date(String(value).replace(" ", "T"));
		if (isNaN(date.getTime())) {
			return this.escape(value);
		}
		return this.escape(
			date.toLocaleString(undefined, {
				year: "numeric",
				month: "short",
				day: "2-digit",
				hour: "2-digit",
				minute: "2-digit",
			})
		);
	},

	format_date(value) {
		if (!value) {
			return "<span class=\"al-dispatch-muted\">-</span>";
		}
		const date = new Date(String(value));
		if (isNaN(date.getTime())) {
			return this.escape(value);
		}
		return this.escape(date.toLocaleDateString());
	},

	status_badge(status) {
		if (!status) {
			return "<span class=\"al-dispatch-muted\">-</span>";
		}
		const label = String(status).replace(/_/g, " ");
		return `<span class="al-dispatch-badge st-${this.escape(String(status).toUpperCase())}">${this.escape(
			label
		)}</span>`;
	},

	verification_badge(status) {
		if (!status) {
			return "<span class=\"al-dispatch-muted\">-</span>";
		}
		const tone = String(status).toLowerCase().startsWith("pending")
			? "pending"
			: String(status).toLowerCase();
		const label = String(status).replace(/_/g, " ");
		return `<span class="al-dispatch-badge tone-${this.escape(tone)}">${this.escape(label)}</span>`;
	},

	panel(title, subtitle, body, extra_class) {
		return `<section class="al-dispatch-panel ${extra_class || ""}">
			<header class="al-dispatch-panel-head">
				<div>
					<h3 class="al-dispatch-panel-title">${this.escape(title)}</h3>
					${
						subtitle
							? `<p class="al-dispatch-panel-sub">${this.escape(subtitle)}</p>`
							: ""
					}
				</div>
			</header>
			<div class="al-dispatch-panel-body">${body}</div>
		</section>`;
	},

	table_html(columns, rows) {
		const head = columns
			.map(
				(column) =>
					`<th class="${column.numeric ? "col-numeric" : ""}">${this.escape(column.label)}</th>`
			)
			.join("");
		const body = rows
			.map((row) => `<tr>${row.map((cell, index) => this.cell_html(cell, columns[index])).join("")}</tr>`)
			.join("");
		return `<div class="al-dispatch-table-wrap">
			<table class="al-dispatch-table">
				<thead><tr>${head}</tr></thead>
				<tbody>${body}</tbody>
			</table>
		</div>`;
	},

	cell_html(cell, column) {
		const classes = [column && column.numeric ? "col-numeric" : "", column && column.actions ? "col-actions" : ""]
			.filter(Boolean)
			.join(" ");
		return `<td class="${classes}">${cell === undefined || cell === null || cell === "" ? "<span class=\"al-dispatch-muted\">-</span>" : cell}</td>`;
	},

	empty_state(message) {
		return `<div class="al-dispatch-empty">${this.escape(message)}</div>`;
	},

	server_message(error) {
		if (!error) {
			return "";
		}
		if (error._server_messages) {
			try {
				const messages = frappe.parse_json(error._server_messages);
				if (messages && messages.length) {
					const first = frappe.parse_json(messages[0]);
					return first ? first.message || first : "";
				}
			} catch (e) {
				// ignore parse failures and fall back to the generic message
			}
		}
		return error.message || error.exc || "";
	},
};
