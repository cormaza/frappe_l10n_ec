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
};
