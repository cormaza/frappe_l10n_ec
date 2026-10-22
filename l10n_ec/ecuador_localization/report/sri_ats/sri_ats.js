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
