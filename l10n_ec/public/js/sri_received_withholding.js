// Import a customer-issued withholding XML (07) into a draft batch.
// The SRI number, authorization (clave offline) and per-invoice IR/IVA
// come from the file; the customer must already exist (fail loud),
// and sustento docs auto-match authorized sales invoices of that customer.
frappe.ui.form.on("SRI Received Withholding", {
	refresh(frm) {
		if (!frm.is_new()) return;
		frm.add_custom_button(__("Import Customer XML"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Import Customer Withholding XML"),
				fields: [
					{fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"), reqd: 1, default: frappe.defaults.get_user_default("Company")},
					{fieldname: "xml_file", fieldtype: "Attach", label: __("XML File"), reqd: 1, description: __("Signed withholding XML (.xml) where you are the sujeto retenido.")},
				],
				primary_action_label: __("Import as Draft"),
				primary_action(values) {
					dialog.disable_primary_action();
					const input = dialog.fields_dict.xml_file.$input[0].files[0];
					if (!input) { frappe.msgprint(__("Select an XML file first.")); dialog.enable_primary_action(); return; }
					const reader = new FileReader();
					reader.onload = function() {
						frappe.call({
							method: "l10n_ec.ecuador_localization.received_withholding.import_customer_withholding",
							args: {xml_text: reader.result, company: values.company},
							freeze: true,
							freeze_message: __("Importing customer withholding..."),
							callback(r) {
								dialog.hide();
								if (r.message) frappe.set_route("Form", "SRI Received Withholding", r.message);
							},
							error() { dialog.enable_primary_action(); },
						});
					};
					reader.readAsText(input);
				},
			});
			dialog.show();
		});
	},
});
