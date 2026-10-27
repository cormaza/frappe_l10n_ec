// Dynamic SRI sustento options: acota y cambia default según tipo de documento y proveedor.
// Mapa v1: permissivo por tipoComprobante (Tabla 4) — se endurecerá cuando se vendorice catálogo 06-08-2026.
frappe.ui.form.on("Purchase Invoice", {
 refresh(frm) { filter_sustento(frm); },
 supplier(frm) { filter_sustento(frm); },
 sri_is_liquidacion(frm) { filter_sustento(frm); },
 sri_is_supplier_debit_note(frm) { filter_sustento(frm); },
 is_return(frm) { filter_sustento(frm); },
});

function filter_sustento(frm) {
 if (!frm.fields_dict.sri_sustento_code) return;
 const is_return = !!frm.doc.is_return;
 const is_liq = !!frm.doc.sri_is_liquidacion;
 const is_debit = !!frm.doc.sri_is_supplier_debit_note;
 let allowed, defval;
 if (is_return) { allowed = ["01","02","06","07"]; defval = "01"; }
 else if (is_debit) { allowed = ["01","02"]; defval = "01"; }
 else if (is_liq) { allowed = ["02","06","07"]; defval = "02"; }
 else { allowed = ["01","02","03","04","05","06","07","08","09","10","11","12","13","14","15"]; defval = "02"; }
 // Set options filtered
 const df = frappe.meta.get_docfield("Purchase Invoice", "sri_sustento_code", frm.doc.name);
 if (df) {
   const all_opts = "01\n02\n03\n04\n05\n06\n07\n08\n09\n10\n11\n12\n13\n14\n15".split("\n");
   const filtered = all_opts.filter(c => allowed.includes(c));
   df.options = filtered.join("\n");
   frm.refresh_field("sri_sustento_code");
 }
 // Cambia default si el valor actual quedó fuera del allowed o vacío
 if (!frm.doc.sri_sustento_code || !allowed.includes(frm.doc.sri_sustento_code)) {
   frm.set_value("sri_sustento_code", defval);
 }
}

function add_supplier_xml_button(frm) {
 if (!frm.is_new()) return;
 frm.add_custom_button(__("Import Supplier XML"), () => {
  const dialog = new frappe.ui.Dialog({
   title: __("Import Supplier XML"),
   fields: [
    {fieldname: "company", fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")},
    {fieldname: "item_code", fieldtype: "Link", options: "Item", reqd: 1, description: __("Applied to every XML line; the row keeps the XML description.")},
    {fieldname: "sustento", fieldtype: "Select", options: ["01","02","03","04","05","06","07","08","09","10","11","12","13","14","15"].join("\n"), reqd: 1, default: "02"},
    {fieldname: "xml_file", fieldtype: "Attach", reqd: 1, description: __("Signed supplier factura XML (.xml).")},
   ],
   primary_action_label: __("Import as Draft"),
   primary_action(values) {
    dialog.disable_primary_action();
    const reader = new FileReader();
    const input = dialog.fields_dict.xml_file.$input[0].files[0];
    if (!input) { frappe.msgprint(__("Select an XML file first.")); dialog.enable_primary_action(); return; }
    reader.onload = function() {
     frappe.call({
      method: "l10n_ec.ecuador_localization.received_xml.import_supplier_xml",
      args: {xml_text: reader.result, company: values.company, item_code: values.item_code, sustento: values.sustento},
      freeze: true,
      freeze_message: __("Importing supplier XML..."),
      callback(r) {
       dialog.hide();
       if (r.message) frappe.set_route("Form", "Purchase Invoice", r.message);
      },
      error() { dialog.enable_primary_action(); },
     });
    };
    reader.readAsText(input);
   },
  });
  dialog.show();
}

frappe.ui.form.on("Purchase Invoice", {
 refresh(frm) { add_supplier_xml_button(frm); },
});
