import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Stethoscope, Bell, AlertTriangle, MapPin, Search } from 'lucide-react';

const API_BASE = "http://localhost:8000";

const HospitalDashboard = ({ user }) => {
  const [activeTab, setActiveTab] = useState('alerts');
  const [alerts, setAlerts] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Profile state
  const [specializations, setSpecializations] = useState('');
  const [locConfig, setLocConfig] = useState({ lat: '', lng: '', address: '' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const authHeader = { Authorization: `Bearer ${user.access_token}` };
      const [alertRes, appRes] = await Promise.all([
        axios.get(`${API_BASE}/hospital/alerts`, { headers: authHeader }),
        axios.get(`${API_BASE}/hospital/appointments`, { headers: authHeader })
      ]);
      setAlerts(alertRes.data);
      setAppointments(appRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const saveProfile = async () => {
    try {
      await axios.put(`${API_BASE}/hospital/profile`, {
        lat: locConfig.lat,
        lng: locConfig.lng,
        address: locConfig.address,
        specializations: specializations.split(",").map(s => s.trim().toLowerCase())
      }, {
        headers: { Authorization: `Bearer ${user.access_token}` }
      });
      alert('Profile updated and synchronized.');
    } catch (err) {
      alert('Error updating profile');
    }
  };

  const acceptAlert = async (id) => {
    // In a real app, update alert status to "accepted"
    alert("Alert marked as Accepted & Dispatched!");
  };

  if (loading) return <div className="text-center mt-5"><div className="spinner-border text-success"/></div>;

  return (
    <div className="container-fluid py-4 px-md-5">
      <div className="d-flex justify-content-between align-items-end mb-5">
        <div>
          <h1 className="display-6 font-outfit text-navy mb-1 d-flex gap-3 align-items-center">
             <Stethoscope className="text-success" size={32}/> {user.name} Control
          </h1>
          <p className="text-secondary mb-0">Emergency Link & Patient Flow</p>
        </div>
      </div>

      <div className="d-flex gap-3 mb-4 border-bottom pb-2">
        <button onClick={() => setActiveTab('alerts')} className={`btn fw-bold p-0 pb-2 border-0 border-bottom border-3 rounded-0 ${activeTab === 'alerts' ? 'border-primary text-primary' : 'border-transparent text-secondary'}`}>
          <AlertTriangle size={18} className="me-2"/> Active Alerts ({alerts.length})
        </button>
        <button onClick={() => setActiveTab('appts')} className={`btn fw-bold p-0 pb-2 border-0 border-bottom border-3 rounded-0 ${activeTab === 'appts' ? 'border-primary text-primary' : 'border-transparent text-secondary'}`}>
           Appointments ({appointments.length})
        </button>
        <button onClick={() => setActiveTab('config')} className={`btn fw-bold p-0 pb-2 border-0 border-bottom border-3 rounded-0 ${activeTab === 'config' ? 'border-primary text-primary' : 'border-transparent text-secondary'}`}>
           Facility Config
        </button>
      </div>

      <div className="row g-4">
        {activeTab === 'alerts' && (
          <div className="col-12 animate-in fade-in">
            {alerts.length === 0 ? (
               <div className="glass-card p-5 text-center text-secondary">
                 <Bell size={48} className="opacity-50 mb-3" />
                 <h4>No Active Emergencies</h4>
                 <p>Your regional sector is currently calm.</p>
               </div>
            ) : (
               alerts.map(a => (
                 <div key={a.id} className="glass-card bg-danger bg-opacity-10 border border-danger p-4 mb-3">
                    <div className="d-flex justify-content-between align-items-start">
                      <div>
                        <h4 className="text-danger fw-bold text-uppercase d-flex align-items-center gap-2">
                          <AlertTriangle size={24}/> {a.category}
                        </h4>
                        <p className="text-dark mb-1">Incoming Dispatch | Coordinates: {a.lat}, {a.lng}</p>
                        <p className="small text-muted mb-0">Dispatched: {new Date(a.created_at).toLocaleTimeString()}</p>
                      </div>
                      <button onClick={() => acceptAlert(a.id)} className="btn btn-danger fw-bold shadow">
                        Accept Patient
                      </button>
                    </div>
                 </div>
               ))
            )}
          </div>
        )}

        {activeTab === 'config' && (
          <div className="col-md-8 mx-auto animate-in scale-in">
            <div className="glass-card p-5">
              <h4 className="mb-4 text-navy">Facility Positioning & Network Core</h4>
              <div className="mb-4">
                <label className="form-label font-bold x-small text-uppercase">Specializations (Comma separated)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. cardio, multispecialist, trauma"
                  value={specializations}
                  onChange={(e) => setSpecializations(e.target.value)}
                />
              </div>
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <label className="form-label font-bold x-small text-uppercase">GPS Coordinates (Lat / Lng)</label>
                  <div className="d-flex gap-2">
                     <input type="text" className="form-control" placeholder="Latitude" value={locConfig.lat} onChange={(e) => setLocConfig({...locConfig, lat: e.target.value})} />
                     <input type="text" className="form-control" placeholder="Longitude" value={locConfig.lng} onChange={(e) => setLocConfig({...locConfig, lng: e.target.value})} />
                  </div>
                  <button className="btn btn-sm btn-outline-secondary mt-2" onClick={() => {
                     navigator.geolocation.getCurrentPosition(p => setLocConfig({...locConfig, lat: p.coords.latitude, lng: p.coords.longitude}))
                  }}>
                     <MapPin size={14}/> Detect My Facility
                  </button>
                </div>
              </div>
              <button className="btn btn-success fw-bold px-5" onClick={saveProfile}>Synchronize Facility</button>
            </div>
          </div>
        )}

        {activeTab === 'appts' && (
           <div className="col-12 animate-in fade-in">
              <div className="glass-card p-5 text-center text-secondary">
                 <Search size={48} className="opacity-50 mb-3" />
                 <h4>No Appointments</h4>
                 <p>Patient flow is empty.</p>
               </div>
           </div>
        )}
      </div>
    </div>
  );
};

export default HospitalDashboard;
