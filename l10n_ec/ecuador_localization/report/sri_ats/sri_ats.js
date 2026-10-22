// SRI ATS filters: company (Ecuador only), year, month.
frappe.query_reports["SRI ATS"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
			get_query() {
				return { filters: { country: "Ecuador" } };
			},
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Int",
			default: new Date().getFullYear(),
			reqd: 1,
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Int",
			default: new Date().getMonth() + 1,
			reqd: 1,
		},
	],
	onload(report) {
		frappe.call({
			method: "l10n_ec.sri.ats_validator.validator_status",
			callback(r) {
				const status = r.message || {};
				if (!status.reachable) {
					report.page.set_indicator(__("Validator unavailable"), "grey");
				} else if (status.stale) {
					report.page.set_indicator(__("Outdated validator: {0}", [status.reason]), "red");
				} else {
					const versions = status.reported || {};
					report.page.set_indicator(
						__("Validator {0}", [versions.sriPluginZip || "?"]),
						"green"
					);
				}
			},
		});
		report.page.add_inner_button(__("Validate in DIMM"), () => {
			const values = report.get_values();
			if (!values.company || !values.year || !values.month) {
				frappe.msgprint(__("Set Company, Year and Month before validating."));
				return;
			}
			frappe.call({
				method: "l10n_ec.sri.ats_validator.validate_month",
				args: {
					company: values.company,
					year: values.year,
					month: values.month,
				},
				freeze: true,
				freeze_message: __("Validating ATS files…"),
				callback(r) {
					const receipt = r.message || {};
					const versions = receipt.versions || {};
					const counts = receipt.counts || {};
					const lines = (receipt.messages || [])
						.map((m) => `<li>${frappe.utils.escape_html(m)}</li>`)
						.join("");
					const stale = receipt.stale
						? `<p class="text-danger"><b>${__("Outdated validator")}:</b> ${frappe.utils.escape_html(receipt.reason || "")}</p>`
						: "";
					const findings = (receipt.messages || []).length
						? `<p><b>${__("{0} findings", [(receipt.messages || []).length])}:</b></p><ul class="small" style="max-height:160px;overflow:auto">${lines}</ul>`
						: `<p class="text-muted">${__("No errors or warnings reported by DIMM.")}</p>`;
					const talon = receipt.talon_html
						? `<hr><p><b>${__("DIMM summary (talón)")}</b></p><iframe class="ats-talon-frame" style="width:100%;height:420px;border:1px solid var(--border-color)"></iframe>`
						: "";
					const dialog = new frappe.ui.Dialog({
						title: __("DIMM verdict: {0}", [receipt.verdict || "?"]),
						width: 900,
						fields: [
							{
								fieldtype: "HTML",
								options: `<p>${__("Validator {0}", [versions.sriPluginZip || "?"])} · ${__("Documents: {0} purchases, {1} sales.", [counts.compras || 0, counts.ventas || 0])}</p>${stale}${findings}${talon}`,
							},
						],
					});
					dialog.show();
					const frame = dialog.body.querySelector("iframe.ats-talon-frame");
					if (frame && receipt.talon_html) frame.srcdoc = receipt.talon_html;
				}
			});
		});
		report.page.add_inner_button(__("Download ATS ZIP"), () => {
			const values = report.get_values();
			if (!values.company || !values.year || !values.month) {
				frappe.msgprint(__("Set Company, Year and Month before downloading."));
				return;
			}
			frappe.call({
				method:
					"l10n_ec.ecuador_localization.report.sri_ats.sri_ats.download_ats",
				args: {
					company: values.company,
					year: values.year,
					month: values.month,
				},
				freeze: true,
				freeze_message: __("Generating ATS files…"),
				callback(r) {
					if (!r.message) return;
					const counts = r.message.counts || {};
					frappe.msgprint({
						title: __("ATS generated"),
						message: __("Documents: {0} purchases, {1} sales.", [
							counts.compras || 0,
							counts.ventas || 0,
						]),
					});
					window.open(r.message.zip);
				}
			});
		});
	},
};
