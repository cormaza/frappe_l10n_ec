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
