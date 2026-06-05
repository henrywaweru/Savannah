import { useRef } from 'react';

export function ReceiptModal({ receipt, onClose }) {
  const printRef = useRef();

  const handlePrint = () => {
    const styles = `
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: 'Segoe UI', Arial, sans-serif; background: #fff; color: #111; }
      .page { max-width: 560px; margin: 40px auto; padding: 40px; border: 1px solid #e5e7eb; border-radius: 12px; }
      .header { display: flex; align-items: center; gap: 12px; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 2px solid #f3f4f6; }
      .logo-box { width: 44px; height: 44px; background: #1a56db; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
      .logo-box svg { display: block; }
      .logo-text { font-size: 20px; font-weight: 700; color: #111; }
      .logo-sub { font-size: 12px; color: #6b7280; margin-top: 2px; }
      .title { font-size: 22px; font-weight: 700; color: #111; margin-bottom: 4px; }
      .subtitle { color: #6b7280; font-size: 13px; margin-bottom: 24px; }
      .badge { display: inline-flex; align-items: center; gap: 6px; background: #f0fdf4; color: #15803d; padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 28px; border: 1px solid #bbf7d0; }
      .amount-box { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 28px; }
      .amount-label { color: #6b7280; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
      .amount-value { font-size: 42px; font-weight: 800; color: #1a56db; letter-spacing: -1px; }
      .row { display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid #f9fafb; }
      .row:last-child { border-bottom: none; }
      .row-label { color: #6b7280; font-size: 13px; }
      .row-value { font-weight: 600; color: #111; font-size: 13px; text-align: right; }
      .footer { margin-top: 28px; padding-top: 20px; border-top: 1px solid #f3f4f6; text-align: center; }
      .footer p { color: #9ca3af; font-size: 11px; line-height: 1.8; }
      .watermark { color: #1a56db; font-weight: 700; font-size: 12px; margin-bottom: 4px; }
      @media print {
        body { margin: 0; }
        .page { border: none; margin: 0; border-radius: 0; max-width: 100%; }
      }
    `;

    const win = window.open('', '_blank', 'width=700,height=900');
    win.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Receipt ${receipt.ref || receipt.receipt || ''} — Savannah PMS</title>
        <style>${styles}</style>
      </head>
      <body>
        <div class="page">
          <div class="header">
            <div class="logo-box">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6"/>
              </svg>
            </div>
            <div>
              <div class="logo-text">Savannah PMS</div>
              <div class="logo-sub">Property Management System</div>
            </div>
          </div>

          <div class="title">Payment Receipt</div>
          <div class="subtitle">Official Rent Payment Confirmation</div>

          <div class="badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#15803d" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
            Payment Successful
          </div>

          <div class="amount-box">
            <div class="amount-label">Amount Paid</div>
            <div class="amount-value">KES ${Number(receipt.amount || 0).toLocaleString()}</div>
          </div>

          <div class="row"><span class="row-label">Receipt Number</span><span class="row-value">${receipt.ref || receipt.receipt || 'N/A'}</span></div>
          <div class="row"><span class="row-label">Tenant Name</span><span class="row-value">${receipt.tenant || 'N/A'}</span></div>
          <div class="row"><span class="row-label">Unit</span><span class="row-value">${receipt.unit || 'N/A'}</span></div>
          <div class="row"><span class="row-label">Payment Method</span><span class="row-value">${receipt.method || 'M-Pesa'}</span></div>
          <div class="row"><span class="row-label">Date</span><span class="row-value">${receipt.date || new Date().toLocaleDateString('en-KE', { year: 'numeric', month: 'long', day: 'numeric' })}</span></div>
          <div class="row"><span class="row-label">Status</span><span class="row-value" style="color:#15803d;">Completed</span></div>

          <div class="footer">
            <div class="watermark">Savannah Property Management System</div>
            <p>This is an official payment receipt. Keep for your records.</p>
            <p>Generated on ${new Date().toLocaleString('en-KE')}</p>
          </div>
        </div>
      </body>
      </html>
    `);
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 500);
  };

  if (!receipt) return null;

  const rows = [
    ["Receipt No.", receipt.ref || receipt.receipt || 'N/A'],
    ["Tenant", receipt.tenant || 'N/A'],
    ["Unit", receipt.unit || 'N/A'],
    ["Method", receipt.method || 'M-Pesa'],
    ["Date", receipt.date || new Date().toLocaleDateString('en-KE')],
    ["Status", "Completed"],
  ];

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 999, padding: 20 }}>
      <div style={{ background: "#fff", borderRadius: 18, width: "100%", maxWidth: 500, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 24px 80px rgba(0,0,0,0.2)", fontFamily: "'Outfit','Segoe UI',sans-serif" }}>

        {/* Modal header */}
        <div style={{ padding: "20px 24px", borderBottom: "1px solid #f3f4f6", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <p style={{ fontSize: 15, fontWeight: 700, color: "#111" }}>Payment Receipt</p>
            <p style={{ fontSize: 12, color: "#9ca3af", marginTop: 2 }}>Official confirmation</p>
          </div>
          <button onClick={onClose} style={{ background: "#f3f4f6", border: "none", borderRadius: 8, width: 32, height: 32, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "#6b7280", fontSize: 18 }}>×</button>
        </div>

        {/* Receipt preview */}
        <div style={{ padding: "24px" }} ref={printRef}>
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <div style={{ width: 38, height: 38, borderRadius: 10, background: "#1a56db", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6"/>
              </svg>
            </div>
            <div>
              <p style={{ fontSize: 14, fontWeight: 700, color: "#111" }}>Savannah PMS</p>
              <p style={{ fontSize: 11, color: "#9ca3af" }}>Property Management System</p>
            </div>
          </div>

          <p style={{ fontSize: 18, fontWeight: 700, color: "#111", marginBottom: 4 }}>Payment Receipt</p>
          <p style={{ fontSize: 12, color: "#6b7280", marginBottom: 20 }}>Official Rent Payment Confirmation</p>

          {/* Success badge */}
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "#f0fdf4", color: "#15803d", padding: "7px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600, marginBottom: 22, border: "1px solid #bbf7d0" }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#15803d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
            Payment Successful
          </div>

          {/* Amount */}
          <div style={{ background: "#f8fafc", border: "1px solid #e5e7eb", borderRadius: 12, padding: "20px", textAlign: "center", marginBottom: 22 }}>
            <p style={{ color: "#6b7280", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Amount Paid</p>
            <p style={{ fontSize: 36, fontWeight: 800, color: "#1a56db", letterSpacing: -1 }}>KES {Number(receipt.amount || 0).toLocaleString()}</p>
          </div>

          {/* Details */}
          {rows.map(([label, value]) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid #f9fafb" }}>
              <span style={{ color: "#6b7280", fontSize: 13 }}>{label}</span>
              <span style={{ fontWeight: 600, color: label === "Status" ? "#15803d" : "#111", fontSize: 13 }}>{value}</span>
            </div>
          ))}

          {/* Footer */}
          <div style={{ marginTop: 22, paddingTop: 18, borderTop: "1px solid #f3f4f6", textAlign: "center" }}>
            <p style={{ color: "#1a56db", fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Savannah Property Management System</p>
            <p style={{ color: "#9ca3af", fontSize: 11, lineHeight: 1.7 }}>This is an official payment receipt. Keep for your records.</p>
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ padding: "16px 24px", borderTop: "1px solid #f3f4f6", display: "flex", gap: 10 }}>
          <button onClick={onClose} style={{ flex: 1, padding: "11px", borderRadius: 9, border: "1px solid #e5e7eb", background: "none", color: "#6b7280", fontSize: 13, fontWeight: 500, cursor: "pointer", fontFamily: "inherit" }}>
            Close
          </button>
          <button onClick={handlePrint} style={{ flex: 2, padding: "11px", borderRadius: 9, border: "none", background: "#1a56db", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2M6 14h12v8H6z"/>
            </svg>
            Download / Print PDF
          </button>
        </div>
      </div>
    </div>
  );
}
