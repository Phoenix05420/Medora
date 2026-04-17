import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertTriangle, MapPin, X, HeartPulse, ShieldAlert, Navigation } from 'lucide-react';

const API_BASE = "http://localhost:8000";

const EmergencyFlow = ({ user, onClose }) => {
  const [step, setStep] = useState(1);
  const [category, setCategory] = useState('');
  const [location, setLocation] = useState(null);
  const [dispatchResult, setDispatchResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const categories = [
    { id: 'Heart Pain', icon: <HeartPulse size={32}/>, color: 'bg-danger' },
    { id: 'Road Accident', icon: <AlertTriangle size={32}/>, color: 'bg-warning text-dark' },
    { id: 'Severe Bleeding', icon: <ShieldAlert size={32}/>, color: 'bg-danger' },
    { id: 'Stroke', icon: <HeartPulse size={32}/>, color: 'bg-danger text-light' },
    { id: 'General Traumatic', icon: <AlertTriangle size={32}/>, color: 'bg-secondary text-white' }
  ];

  useEffect(() => {
    // Attempt to grab location immediately upon opening
    if(navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        (err) => console.log("Loc err", err)
      );
    }
  }, []);

  const handleDispatch = async (selectedCat) => {
    setCategory(selectedCat);
    setStep(2);
    setLoading(true);

    try {
      // If location failed, use a dummy loc for demo
      const payloadLoc = location || { lat: 51.5, lng: -0.1 };
      
      const res = await axios.post(`${API_BASE}/emergency/alert`, {
        category: selectedCat,
        lat: String(payloadLoc.lat),
        lng: String(payloadLoc.lng)
      }, {
        headers: { Authorization: `Bearer ${user.access_token}` }
      });

      setDispatchResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Dispatch failed. No responsive vehicles/hospitals available.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vh-100 bg-danger bg-opacity-10 d-flex flex-column align-items-center justify-content-center position-fixed top-0 start-0 w-100 z-index-100 p-4 animate-in fade-in" style={{ zIndex: 9999, backdropFilter: 'blur(10px)' }}>
      <button onClick={onClose} className="btn btn-dark rounded-circle position-absolute top-0 end-0 m-4 shadow" style={{ width: 48, height: 48}}>
        <X size={24} />
      </button>

      {step === 1 && (
        <div className="text-center w-100 max-w-md animate-in slide-in-bottom">
          <div className="bg-danger text-white rounded-circle d-inline-flex p-4 shadow-lg mb-4 pulse-animation">
            <AlertTriangle size={64} />
          </div>
          <h1 className="display-4 fw-black text-danger mb-2 tracking-tight uppercase">Emergency SOS</h1>
          <p className="lead fw-bold mb-5 text-dark">Classify the situation for immediate regional dispatch.</p>

          <div className="row g-3 justify-content-center" style={{ maxWidth: '600px', margin: '0 auto'}}>
            {categories.map((c) => (
              <div className="col-12 col-md-6" key={c.id}>
                <button 
                  onClick={() => handleDispatch(c.id)}
                  className={`btn ${c.color} btn-lg w-100 py-4 d-flex flex-column align-items-center gap-2 shadow hover-lift border-0`}
                >
                  {c.icon}
                  <span className="fw-black h5 mb-0 text-uppercase tracking-wider">{c.id}</span>
                </button>
              </div>
            ))}
          </div>

          <div className="mt-5 text-secondary fw-bold d-flex align-items-center justify-content-center gap-2">
            <MapPin size={18} className={location ? "text-success" : "text-warning"} />
            {location ? `GPS Active: ${location.lat.toFixed(3)}, ${location.lng.toFixed(3)}` : 'Acquiring Satellite Lock...'}
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="text-center bg-white p-5 rounded-5 shadow-lg w-100 max-w-md">
          {loading ? (
             <div className="py-5">
               <div className="spinner-grow text-danger mb-4" style={{ width: '4rem', height: '4rem' }} role="status"></div>
               <h3 className="fw-bold tracking-tight">Computing Trajectory...</h3>
               <p className="text-muted">Scanning radar for nearest {category} specialists.</p>
             </div>
          ) : error ? (
            <div className="py-4">
              <ShieldAlert size={64} className="text-warning mb-3" />
              <h3 className="fw-bold tracking-tight text-danger">DISPATCH ERROR</h3>
              <p>{error}</p>
              <button className="btn btn-outline-danger w-100 fw-bold mt-3" onClick={() => setStep(1)}>Retry Scan</button>
            </div>
          ) : (
            <div className="py-4 animate-in fade-in">
              <div className="bg-success text-white rounded-circle d-inline-flex p-4 shadow mb-4 pulse-animation">
                <Navigation size={48} />
              </div>
              <h2 className="fw-black text-success tracking-tight uppercase mb-2">Unit Dispatched!</h2>
              <div className="bg-light p-3 rounded-4 mb-4 text-start">
                 <p className="mb-1 x-small text-secondary text-uppercase fw-bold tracking-widest">Matched Facility</p>
                 <h4 className="fw-bold text-navy mb-0">{dispatchResult.hospital_name}</h4>
                 <hr className="my-2" />
                 <p className="mb-1 x-small text-secondary text-uppercase fw-bold tracking-widest">Distance</p>
                 <h5 className="fw-bold text-danger mb-0">{dispatchResult.distance_km} KM Away</h5>
              </div>
              
              <div className="alert alert-warning border-warning border-2 fw-bold text-dark mb-4">
                 Stay calm. An ambulance unit has been successfully dispatched to your coordinate location.
              </div>

              <button className="btn btn-dark btn-lg w-100 fw-bold" onClick={onClose}>Close Overlay</button>
            </div>
          )}
        </div>
      )}

      <style>{`
        .hover-lift { transition: transform 0.2s cubic-bezier(.4,0,.2,1); }
        .hover-lift:hover { transform: translateY(-4px); }
        .pulse-animation { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.4); } 70% { box-shadow: 0 0 0 20px rgba(220, 53, 69, 0); } 100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); } }
      `}</style>
    </div>
  );
};

export default EmergencyFlow;
