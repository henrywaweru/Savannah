import { useState, useRef } from 'react';


const API_BASE = import.meta.env.VITE_API_URL || "https://savannah-backend-kcxm.onrender.com";

function MpesaPayment({ tenantId, propertyId, token, onSuccess, onError }) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [customAmount, setCustomAmount] = useState('');
  const [status, setStatus] = useState(null); // null | 'sending' | 'pending' | 'completed' | 'failed' | 'timeout'
  const [message, setMessage] = useState('');
  const [receipt, setReceipt] = useState(null);
  const [checkoutId, setCheckoutId] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const intervalRef = useRef(null);

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const amount = parseFloat(customAmount) || 0;
  const canSubmit = phoneNumber.length === 9 && amount >= 1 && status !== 'sending';

  const initiatePayment = async () => {
    setStatus('sending');
    setMessage('');
    setReceipt(null);

    try {
      const authToken = token || sessionStorage.getItem('token');
      if (!token) throw new Error('Session expired. Please log in again.');

      const response = await fetch(`${API_BASE}/api/mpesa/stkpush`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          tenant_id: tenantId,
          amount: amount,
          phone_number: '254' + phoneNumber,
          property_id: propertyId,
        }),
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setCheckoutId(data.checkout_request_id);
        setStatus('pending');
        setMessage('Enter your M-Pesa PIN on +254' + phoneNumber);
        pollPaymentStatus(data.checkout_request_id);
      } else {
        throw new Error(data.detail || 'Could not send payment request. Try again.');
      }
    } catch (error) {
      setStatus('failed');
      setMessage(error.message);
      if (onError) onError(error.message);
    }
  };

  const pollPaymentStatus = (id) => {
    let attempts = 0;
    intervalRef.current = setInterval(async () => {
      attempts++;
      try {
      const authToken = token || sessionStorage.getItem('token');
        const res = await fetch(`${API_BASE}/api/mpesa/status/${id}`, {
          headers: { 'Authorization': `Bearer ${authToken}` },
        });
        const data = await res.json();

        if (data.status === 'completed') {
          stopPolling();
          setStatus('completed');
          setMessage(`KES ${amount.toLocaleString()} received successfully.`);
          if (onSuccess) onSuccess();
        } else if (data.status === 'failed') {
          stopPolling();
          setStatus('failed');
          setMessage(data.result_desc || 'Payment was cancelled or failed.');
        } else if (attempts >= 30) {
          stopPolling();
          setStatus('timeout');
          setMessage('No response after 90 seconds. Use "Simulate Payment" below to complete.');
        }
      } catch {
        // network hiccup — keep polling
      }
    }, 3000);
  };

  // Sandbox only: manually trigger confirmation
  const simulatePayment = async () => {
    if (!checkoutId) return;
    setSimulating(true);
    try {
      const res = await fetch(`${API_BASE}/api/mpesa/simulate/${checkoutId}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (res.ok && data.status === 'completed') {
        stopPolling();
        setStatus('completed');
        setReceipt(data.receipt);
        setMessage(`KES ${amount.toLocaleString()} received successfully.`);
        if (onSuccess) onSuccess();
      } else {
        setMessage(data.detail || 'Simulation failed. Try again.');
      }
    } catch {
      setMessage('Could not reach server. Check your connection.');
    } finally {
      setSimulating(false);
    }
  };

  const reset = () => {
    stopPolling();
    setStatus(null);
    setMessage('');
    setReceipt(null);
    setCheckoutId(null);
    setPhoneNumber('');
    setCustomAmount('');
  };

  const handlePhoneChange = (e) => {
    const digits = e.target.value.replace(/\D/g, '').replace(/^0/, '');
    if (digits.length <= 9) setPhoneNumber(digits);
  };

  const handleAmountChange = (e) => {
    const val = e.target.value.replace(/[^0-9]/g, '');
    setCustomAmount(val);
  };

  // ── Styles ──────────────────────────────────────────
  const card = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 16,
    padding: '24px',
    maxWidth: 420,
    margin: '0 auto',
    fontFamily: "'DM Sans','Segoe UI',sans-serif",
    color: '#f1f5f9',
  };
  const label = {
    display: 'block', fontSize: 11, fontWeight: 600,
    color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6,
  };
  const input = {
    width: '100%', padding: '10px 14px', fontSize: 14,
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 10, color: '#f1f5f9',
    boxSizing: 'border-box',
  };
  const prefix = {
    display: 'flex', alignItems: 'center', padding: '0 12px',
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRight: 'none',
    borderRadius: '10px 0 0 10px',
    fontSize: 13, color: '#64748b',
  };
  const btnGreen = {
    width: '100%', padding: '12px 0', fontSize: 14, fontWeight: 600,
    background: canSubmit ? 'linear-gradient(135deg,#10b981,#059669)' : 'rgba(255,255,255,0.05)',
    color: canSubmit ? '#fff' : '#475569',
    border: 'none', borderRadius: 10, cursor: canSubmit ? 'pointer' : 'not-allowed',
    transition: 'all 0.15s',
  };

  return (
    <div style={card}>
      <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 20, color: '#f1f5f9' }}>
        Pay with M-Pesa
      </p>

      {/* ── FORM ── */}
      {(!status || status === 'sending') && (
        <>
          {/* Amount */}
          <div style={{ marginBottom: 16 }}>
            <label style={label}>Amount (KES)</label>
            <div style={{ position: 'relative' }}>
              <span style={{
                position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
                fontSize: 13, color: '#64748b',
              }}>KES</span>
              <input
                type="text"
                inputMode="numeric"
                placeholder="e.g. 5000"
                value={customAmount}
                onChange={handleAmountChange}
                style={{ ...input, paddingLeft: 48 }}
              />
            </div>
            {amount > 0 && (
              <p style={{ fontSize: 11, color: '#10b981', marginTop: 4 }}>
                You will pay KES {amount.toLocaleString()}
              </p>
            )}
          </div>

          {/* Phone */}
          <div style={{ marginBottom: 20 }}>
            <label style={label}>M-Pesa Phone Number</label>
            <div style={{ display: 'flex' }}>
              <span style={prefix}>+254</span>
              <input
                type="tel"
                placeholder="712 345 678"
                value={phoneNumber}
                onChange={handlePhoneChange}
                disabled={status === 'sending'}
                style={{
                  ...input,
                  borderRadius: '0 10px 10px 0',
                  flex: 1,
                  width: 'auto',
                }}
              />
            </div>
            <p style={{ fontSize: 11, color: '#475569', marginTop: 4 }}>
              9 digits, no leading zero
            </p>
          </div>

          <button onClick={initiatePayment} disabled={!canSubmit} style={btnGreen}>
            {status === 'sending' ? 'Sending request...' : 'Send M-Pesa Prompt →'}
          </button>
        </>
      )}

      {/* ── PENDING ── */}
      {status === 'pending' && (
        <div style={{ textAlign: 'center', padding: '8px 0' }}>
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          <div style={{
            width: 52, height: 52, borderRadius: '50%',
            border: '3px solid rgba(16,185,129,0.2)', borderTopColor: '#10b981',
            margin: '0 auto 16px', animation: 'spin 0.9s linear infinite',
          }} />
          <p style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>Check your phone</p>
          <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 4 }}>{message}</p>
          <p style={{ fontSize: 11, color: '#475569', marginBottom: 24 }}>
            Waiting for confirmation...
          </p>

          {/* Sandbox simulate button */}
          <div style={{
            background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)',
            borderRadius: 12, padding: '14px 16px', marginBottom: 16, textAlign: 'left',
          }}>
            <p style={{ fontSize: 12, color: '#fbbf24', fontWeight: 600, marginBottom: 4 }}>
              Sandbox mode
            </p>
            <p style={{ fontSize: 11, color: '#92400e', marginBottom: 12 }}>
              No real prompt is sent to your phone. Click below to simulate a successful payment.
            </p>
            <button
              onClick={simulatePayment}
              disabled={simulating}
              style={{
                width: '100%', padding: '10px 0', fontSize: 13, fontWeight: 600,
                background: simulating ? 'rgba(255,255,255,0.05)' : 'linear-gradient(135deg,#10b981,#059669)',
                color: simulating ? '#475569' : '#fff',
                border: 'none', borderRadius: 8, cursor: simulating ? 'not-allowed' : 'pointer',
              }}
            >
              {simulating ? 'Processing...' : '✓ Simulate Payment'}
            </button>
          </div>

          <button onClick={reset} style={{
            fontSize: 12, background: 'none', border: 'none',
            color: '#475569', cursor: 'pointer', textDecoration: 'underline',
          }}>Cancel</button>
        </div>
      )}

      {/* ── SUCCESS ── */}
      {status === 'completed' && (
        <div style={{ textAlign: 'center', padding: '8px 0' }}>
          <div style={{
            width: 56, height: 56, borderRadius: '50%',
            background: 'rgba(16,185,129,0.1)', border: '2px solid #10b981',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <svg width="24" height="24" fill="none" stroke="#10b981" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p style={{ fontWeight: 600, fontSize: 16, color: '#10b981', marginBottom: 6 }}>
            Payment Successful
          </p>
          <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 8 }}>{message}</p>
          {receipt && (
            <p style={{ fontSize: 11, color: '#475569', marginBottom: 20 }}>
              Receipt: <span style={{ color: '#64748b', fontFamily: 'monospace' }}>{receipt}</span>
            </p>
          )}
          <button onClick={reset} style={{
            padding: '8px 24px', borderRadius: 8, fontSize: 13,
            background: 'none', border: '1px solid rgba(255,255,255,0.1)',
            color: '#94a3b8', cursor: 'pointer',
          }}>Make Another Payment</button>
        </div>
      )}

      {/* ── FAILED / TIMEOUT ── */}
      {(status === 'failed' || status === 'timeout') && (
        <div style={{ textAlign: 'center', padding: '8px 0' }}>
          <div style={{
            width: 56, height: 56, borderRadius: '50%',
            background: status === 'timeout' ? 'rgba(251,191,36,0.1)' : 'rgba(239,68,68,0.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <svg width="22" height="22" fill="none"
              stroke={status === 'timeout' ? '#fbbf24' : '#ef4444'}
              strokeWidth="2.5" viewBox="0 0 24 24">
              {status === 'timeout'
                ? <><circle cx="12" cy="12" r="10"/><path strokeLinecap="round" d="M12 8v4l3 3"/></>
                : <path strokeLinecap="round" d="M6 18L18 6M6 6l12 12"/>}
            </svg>
          </div>
          <p style={{ fontWeight: 600, fontSize: 15, color: status === 'timeout' ? '#fbbf24' : '#ef4444', marginBottom: 6 }}>
            {status === 'timeout' ? 'Request timed out' : 'Payment not completed'}
          </p>
          <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 20 }}>{message}</p>

          {/* Show simulate button on timeout too */}
          {status === 'timeout' && checkoutId && (
            <div style={{
              background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)',
              borderRadius: 12, padding: '14px 16px', marginBottom: 16,
            }}>
              <p style={{ fontSize: 11, color: '#92400e', marginBottom: 10 }}>
                Still want to complete this payment?
              </p>
              <button
                onClick={simulatePayment}
                disabled={simulating}
                style={{
                  width: '100%', padding: '10px 0', fontSize: 13, fontWeight: 600,
                  background: 'linear-gradient(135deg,#10b981,#059669)',
                  color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer',
                }}
              >
                {simulating ? 'Processing...' : '✓ Simulate Payment'}
              </button>
            </div>
          )}

          <button onClick={reset} style={{
            padding: '8px 24px', borderRadius: 8, fontSize: 13,
            background: 'linear-gradient(135deg,#10b981,#059669)',
            color: '#fff', border: 'none', cursor: 'pointer',
          }}>Try Again</button>
        </div>
      )}

      <p style={{
        fontSize: 10, color: '#334155', textAlign: 'center',
        marginTop: 20, paddingTop: 16,
        borderTop: '1px solid rgba(255,255,255,0.05)',
      }}>
        Intasend sandbox · Enter any phone number · Use simulate button to confirm
      </p>
    </div>
  );
}

export default MpesaPayment;
